"""Loguru-based logging provider.

Provides a single logger instance used across the entire service.
Also intercepts the standard `logging` module so that third-party libraries
(uvicorn, SQLAlchemy, alembic, langgraph, etc.) are routed through loguru.
"""

import logging
import sys

from loguru import logger


# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
    "|<level>{level: <8}</level> "
    "| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
    "| <level>{message}</level>"
)


# ---------------------------------------------------------------------------
# Standard-library logging → loguru bridge
# ---------------------------------------------------------------------------

class _InterceptHandler(logging.Handler):
    """Redirect all stdlib logging records into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def configure_logging(level: str = "INFO") -> None:
    """Set up loguru and bridge stdlib logging into it.

    Call once at startup — before any other imports that use logging.
    """
    logger.remove()
    logger.add(sys.stdout, format=LOG_FORMAT, level=level, colorize=True)

    # Intercept everything from the stdlib logging module
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    # Silence noisy third-party loggers at WARNING unless we're in DEBUG
    if level != "DEBUG":
        for noisy in ("sqlalchemy.engine", "httpx", "httpcore", "openai"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger():
    return logger
