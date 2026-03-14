# not-your-it-guy

OpenAI-compatible agent backend. Accepts requests on the [Responses API](https://platform.openai.com/docs/api-reference/responses) format so any off-the-shelf OpenAI client works out of the box.

---

## Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.12 |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Web framework | FastAPI + Uvicorn |
| Models | Pydantic v2 |
| Container | Docker (multi-stage, `python:3.12-slim`) |

---

## Local development

### Prerequisites

- Python 3.12 (via `pyenv` or system install)
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

### Setup

```bash
git clone <repo-url>
cd not-your-it-guy

cp .env.example .env   # edit as needed

uv sync                # creates .venv and installs deps
```

### Run

```bash
uv run uvicorn not_your_it_guy.main:app --host 0.0.0.0 --port 8000 --reload
```

### Test

```bash
# Health check
curl http://localhost:8000/health

# Responses API
curl -s -X POST http://localhost:8000/v1/responses \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","input":"hello"}' | python3 -m json.tool
```

---

## Docker

### Build

```bash
docker build -t not-your-it-guy:dev .
```

### Run

```bash
docker run --rm -p 8000:8000 --env-file .env not-your-it-guy:dev
```

### Test

```bash
curl -s -X POST http://localhost:8000/v1/responses \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","input":"hello from docker"}' | python3 -m json.tool
```

---

## Configuration

All config is via environment variables. Copy `.env.example` to `.env` for local development.

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Set to `true` to enable DEBUG-level console logging |
| `PORT` | `8000` | Port the server listens on (local dev) |

> On Render, set env vars in **Dashboard → Service → Environment**.

---

## API

### `POST /v1/responses`

OpenAI Responses API compatible endpoint.

**Request**
```json
{
  "model": "gpt-4o",
  "input": "your prompt here"
}
```

**Response**
```json
{
  "id": "resp_...",
  "object": "response",
  "created_at": 1234567890,
  "status": "completed",
  "model": "gpt-4o",
  "output": [
    {
      "id": "msg_...",
      "type": "message",
      "role": "assistant",
      "status": "completed",
      "content": [{ "type": "output_text", "text": "Prompt accepted.", "annotations": [] }]
    }
  ],
  "usage": { "input_tokens": 0, "output_tokens": 2, "total_tokens": 2 }
}
```

### `GET /health`

Returns `{"status": "ok"}`.

---

## Project structure

```
src/not_your_it_guy/
├── main.py          # App entry point, logging config, lifespan
├── models.py        # Pydantic request/response models
└── routers/
    └── responses.py # POST /v1/responses handler
```
