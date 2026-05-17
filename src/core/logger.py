import os
import sys
from pathlib import Path

from loguru import logger

from src.core.config import settings

# Determine the absolute project root (parent of src)
PROJECT_ROOT = Path(__file__).parent.parent.parent

def setup_logging() -> None:
    logger.remove()
    
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)

    # Console output
    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        backtrace=False,
        diagnose=False,
    )
    
    # File output
    logger.add(
        str(log_dir / "chatbot.log"),
        rotation="10 MB",
        retention="1 week",
        level=settings.log_level.upper(),
        backtrace=True,
        diagnose=True,
        enqueue=True, # Ensure thread-safe and flushed
    )

setup_logging()

