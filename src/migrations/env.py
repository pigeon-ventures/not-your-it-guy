"""Alembic migration environment."""

from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Walk up to find .env at project root and load it before importing app modules
from dotenv import load_dotenv
_here = Path(__file__).parent
for _candidate in [_here, _here.parent, _here.parent.parent]:
    if (_candidate / ".env").exists():
        load_dotenv(_candidate / ".env", override=True)
        break

from not_your_it_guy.db.models import Base  # noqa: E402
from not_your_it_guy.db.session import get_sync_database_url  # noqa: E402

config = context.config
config.set_main_option("sqlalchemy.url", get_sync_database_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
