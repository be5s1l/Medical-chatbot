import sys

from loguru import logger

from src.core.config import settings


def setup_logging() -> None:
    logger.remove()
    import os
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Console output
    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        backtrace=False,
        diagnose=False,
    )
    
    # File output
    logger.add(
        "logs/chatbot.log",
        rotation="10 MB",
        retention="1 week",
        level=settings.log_level.upper(),
        backtrace=True,
        diagnose=True,
        enqueue=True, # Ensure thread-safe and flushed
    )


setup_logging()

