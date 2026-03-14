"""Application entry point."""

import logging
import logging.config
import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI

from not_your_it_guy.routers import responses

# ---------------------------------------------------------------------------
# Logging — set DEBUG=true env var to enable debug level
# ---------------------------------------------------------------------------

_log_level = "DEBUG" if os.getenv("DEBUG", "").lower() in ("1", "true", "yes") else "INFO"

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "root": {"level": _log_level, "handlers": ["console"]},
    }
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Not Your IT Guy",
    description="OpenAI-compatible agent backend",
    version="0.1.0",
)

app.include_router(responses.router)

logger.info("Starting Not Your IT Guy — log level: %s", _log_level)


@app.get("/health")
async def health() -> dict:
    logger.debug("Health check called")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Dev runner
# ---------------------------------------------------------------------------


def main() -> None:
    uvicorn.run("not_your_it_guy.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
