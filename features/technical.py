import pandas_ta as ta
import pandas as pd

def add_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Moving averages
    df['ema_9'] = ta.ema(df['Close'], length=9)
    df['ema_21'] = ta.ema(df['Close'], length=21)
    df['ema_50'] = ta.ema(df['Close'], length=50)
    df['ema_200'] = ta.ema(df['Close'], length=200)
    # RSI
    df['rsi_14'] = ta.rsi(df['Close'], length=14)
    # MACD
    macd = ta.macd(df['Close'])
    df['macd'] = macd['MACD_12_26_9']
    df['macd_signal'] = macd['MACDs_12_26_9']
    df['macd_hist'] = macd['MACDh_12_26_9']
    # Bollinger Bands
    bbands = ta.bbands(df['Close'], length=20)
    df['bb_high'] = bbands['BBU_20_2.0']
    df['bb_mid'] = bbands['BBM_20_2.0']
    df['bb_low'] = bbands['BBL_20_2.0']
    # ATR
    df['atr_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    # ADX
    adx = ta.adx(df['High'], df['Low'], df['Close'])
    df['adx'] = adx['ADX_14']
    # Volume
    df['vwap'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
    return df
