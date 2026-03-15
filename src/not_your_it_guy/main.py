"""Application entry point."""

import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Walk up from src/not_your_it_guy/ to find .env at project root
_here = Path(__file__).parent
for _candidate in [_here, _here.parent, _here.parent.parent]:
    if (_candidate / ".env").exists():
        load_dotenv(_candidate / ".env", override=True)
        break

# ---------------------------------------------------------------------------
# Logging — configured BEFORE any other imports
# ---------------------------------------------------------------------------

_log_level = "DEBUG" if os.getenv("DEBUG", "").lower() in ("1", "true", "yes") else "INFO"

from not_your_it_guy.logger.logger_provider import configure_logging, get_logger  # noqa: E402

configure_logging(_log_level)
logger = get_logger()

# ---------------------------------------------------------------------------
# App imports (after logging is set up)
# ---------------------------------------------------------------------------

import uvicorn  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi import Depends, FastAPI, HTTPException, status  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.security import HTTPBasic, HTTPBasicCredentials  # noqa: E402
from sqlalchemy_utils import create_database, database_exists  # noqa: E402

from not_your_it_guy.db.session import get_sync_database_url, init_engine  # noqa: E402
from not_your_it_guy.routers import responses  # noqa: E402

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------


def _find_alembic_ini() -> Path:
    for candidate in [
        Path(__file__).parent,
        Path(__file__).parent.parent,
        Path(__file__).parent.parent.parent,
        Path("/app"),
    ]:
        p = candidate / "alembic.ini"
        if p.exists():
            return p
    raise FileNotFoundError("alembic.ini not found")


def setup_database() -> None:
    db_url = get_sync_database_url()
    if not database_exists(db_url):
        create_database(db_url)
        logger.info("Database created.")
    alembic_cfg = Config(str(_find_alembic_ini()))
    command.upgrade(alembic_cfg, "head")
    logger.info("Migrations applied.")
    init_engine()
    logger.info("Async DB engine initialised.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_database()
    yield


app = FastAPI(
    title="Not Your IT Guy",
    description="OpenAI-compatible agent backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(responses.router)

_basic = HTTPBasic()
_FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", "frontend"))
_FRONTEND_INDEX = _FRONTEND_DIR / "index.html"
_FRONTEND_V2_INDEX = _FRONTEND_DIR / "v2" / "index.html"

logger.info("Starting Not Your IT Guy — log level: {}", _log_level)
logger.info("API_TOKEN loaded: {}", "yes" if os.getenv("API_TOKEN") else "NO — auth will reject all requests")


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


@app.get("/health")
async def health() -> dict:
    logger.debug("Health check called")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------


def main() -> None:
    uvicorn.run(
        "not_your_it_guy.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,
    )


def serve() -> None:
    uvicorn.run(
        "not_your_it_guy.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_config=None,
    )


if __name__ == "__main__":
    main()
