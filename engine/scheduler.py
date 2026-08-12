from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def nightly_tasks(app_state):
    logger.info("Starting nightly tasks...")
    # Train LSTM
    from scripts.train_lstm import main as train_lstm
    await train_lstm()
    # Train DQN
    from ai.models.dqn_trainer import DQNTrainer
    trainer = DQNTrainer()
    await trainer.train()
    # Generate synthetic data
    from ai.dream.generator import DreamGenerator
    generator = DreamGenerator()
    df = await app_state.data_fabric.get_candles('BTCUSD', 'D1', limit=2000)
    if not df.empty:
        generator.generate(df, num_samples=5000)
    # Rebuild feature importance
    logger.info("Nightly tasks complete.")

def schedule_nightly(app_state):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(nightly_tasks, CronTrigger(hour=2, minute=0), args=[app_state])
    scheduler.start()
    logger.info("Scheduled nightly tasks at 2 AM.")
