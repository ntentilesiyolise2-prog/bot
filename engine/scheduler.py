from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def nightly_training(app_state):
    logger.info("Starting nightly training...")
    # Train LSTM
    from scripts.train_lstm import main as train_lstm
    await train_lstm()
    # Train DQN
    from ai.models.dqn_trainer import DQNTrainer
    trainer = DQNTrainer()
    await trainer.train()
    # Dream Mode data generation
    from ai.dream.generator import DreamGenerator
    generator = DreamGenerator()
    # Generate synthetic data and save (optional)
    logger.info("Nightly training complete.")

def schedule_tasks(app_state):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(nightly_training, CronTrigger(hour=2, minute=0), args=[app_state])
    scheduler.start()
    logger.info("Scheduled tasks: nightly training at 2 AM.")
