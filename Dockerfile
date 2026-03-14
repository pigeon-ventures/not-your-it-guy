# ── Stage 1: build deps with uv ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY pyproject.toml uv.lock* README.md ./

# Install deps into an isolated venv inside /app/.venv
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and install the project itself
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# ── Stage 2: lean runtime image ──────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy the fully-populated venv from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source (needed at runtime for non-installed editable installs)
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "not_your_it_guy.main:app", "--host", "0.0.0.0", "--port", "8000"]
