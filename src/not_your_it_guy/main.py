"""Application entry point."""

import logging
import logging.config
import os
import secrets
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# Walk up from src/not_your_it_guy/ to find .env at project root
_here = Path(__file__).parent
for _candidate in [_here, _here.parent, _here.parent.parent]:
    if (_candidate / ".env").exists():
        load_dotenv(_candidate / ".env", override=True)
        break
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

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

_basic = HTTPBasic()
_FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", "frontend"))
_FRONTEND_INDEX = _FRONTEND_DIR / "index.html"
_FRONTEND_V2_INDEX = _FRONTEND_DIR / "v2" / "index.html"


def _require_basic_auth(credentials: HTTPBasicCredentials = Depends(_basic)) -> None:
    expected_user = os.getenv("AUTH_USERNAME", "")
    expected_pass = os.getenv("AUTH_PASSWORD", "")
    user_ok = secrets.compare_digest(credentials.username.encode(), expected_user.encode())
    pass_ok = secrets.compare_digest(credentials.password.encode(), expected_pass.encode())
    if not (user_ok and pass_ok):
        logger.warning("Failed basic auth attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.get("/", dependencies=[Depends(_require_basic_auth)])
async def serve_index() -> FileResponse:
    return FileResponse(_FRONTEND_INDEX, media_type="text/html")


@app.get("/v2", dependencies=[Depends(_require_basic_auth)])
async def serve_v2() -> FileResponse:
    return FileResponse(_FRONTEND_V2_INDEX, media_type="text/html")


logger.info("Starting Not Your IT Guy — log level: %s", _log_level)
logger.info("API_TOKEN loaded: %s", "yes" if os.getenv("API_TOKEN") else "NO — auth will reject all requests")


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
