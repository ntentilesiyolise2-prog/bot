import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from utils.logger import setup_logger

logger = setup_logger(__name__)

class EventIntelligence:
    def __init__(self, app_state):
        self.app = app_state
        self.active_events = []
        self.is_event_mode = False
        self.event_flat_time = None

    async def fetch_calendar(self):
        """Fetch economic calendar from free RSS feed (ForexFactory / Tradays)."""
        # ForexFactory RSS (free)
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        root = ET.fromstring(text)
                        events = []
                        for item in root.findall('item'):
                            title = item.find('title').text
                            pub_date = item.find('pubDate').text
                            # Parse time
                            try:
                                dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z')
                            except:
                                continue
                            # Check if high impact (keywords)
                            keywords = ['CPI', 'PPI', 'NFP', 'FOMC', 'Nonfarm', 'Payrolls', 'Inflation', 'Fed', 'Rate Decision', 'GDP', 'Unemployment']
                            if any(k in title for k in keywords):
                                events.append({
                                    'title': title,
                                    'time': dt,
                                    'impact': 'high'
                                })
                        self.active_events = events
                        logger.info(f"📅 Fetched {len(events)} high-impact events.")
                        return events
        except Exception as e:
            logger.error(f"Failed to fetch calendar: {e}")
        return []

    async def monitor_events(self):
        """Check if an event is coming up and act accordingly."""
        if not self.active_events:
            await self.fetch_calendar()
        
        now = datetime.now().astimezone()
        for event in self.active_events:
            event_time = event['time']
            diff = (event_time - now).total_seconds()
            
            # 5 minutes before: flatten positions
            if 300 >= diff > 280 and not self.is_event_mode:
                logger.info(f"⚠️ Event in 5 minutes: {event['title']}. Flattening positions.")
                self.is_event_mode = True
                # Flatten positions
                await self.app.execution_core.broker.flatten_all()
                # Reduce risk
                self.app.config['risk']['max_daily_loss'] = 10.0
                self.event_flat_time = now

            # 2 minutes after event: trade the breakout
            if diff < -120 and self.is_event_mode:
                logger.info(f"📈 Event passed: {event['title']}. Waiting for breakout.")
                # Wait 30 seconds for the spike to settle
                await asyncio.sleep(30)
                # Get 1-min candles after event
                symbol = 'EURUSD'  # You can make this configurable
                df = await self.app.data_fabric.get_candles(symbol, "M1", limit=5)
                if not df.empty:
                    event_candle = df.iloc[-1]
                    high = event_candle['High']
                    low = event_candle['Low']
                    current = df.iloc[-1]['Close']
                    # Breakout logic
                    if current > high:
                        logger.info(f"🚀 Breakout UP detected for {symbol}. Entering BUY.")
                        await self.app.execution_core.execute_order({'symbol': symbol, 'side': 'BUY', 'lot': 0.05})
                    elif current < low:
                        logger.info(f"🚀 Breakout DOWN detected for {symbol}. Entering SELL.")
                        await self.app.execution_core.execute_order({'symbol': symbol, 'side': 'SELL', 'lot': 0.05})
                # Reset mode after trading
                self.is_event_mode = False
                self.event_flat_time = None
