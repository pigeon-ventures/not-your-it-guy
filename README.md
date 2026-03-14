# not-your-it-guy

OpenAI-compatible agent backend. Accepts requests on the [Responses API](https://platform.openai.com/docs/api-reference/responses) format so any off-the-shelf OpenAI client works out of the box.

**Deployed:** `https://not-your-it-guy.onrender.com`

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

cp .env.example .env   # fill in API_TOKEN and other values

uv sync                # creates .venv and installs deps
```

### Run

```bash
uv run uvicorn not_your_it_guy.main:app --host 0.0.0.0 --port 8000 --reload
```

### Test

```bash
export API_TOKEN=your-token-here

# Health check (no auth required)
curl http://localhost:8000/health

# Responses API
curl -s -X POST http://localhost:8000/v1/responses \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","input":"hello"}' | jq
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
export API_TOKEN=your-token-here

curl -s -X POST http://localhost:8000/v1/responses \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","input":"hello from docker"}' | jq
```

---

## Deployed on Render

```bash
export API_TOKEN=your-token-here

# Health check
curl https://not-your-it-guy.onrender.com/health

# Responses API
curl -s -X POST https://not-your-it-guy.onrender.com/v1/responses \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","input":"hello"}' | jq
```

---

## Configuration

All config is via environment variables. Copy `.env.example` to `.env` for local development.

| Variable | Default | Description |
|----------|---------|-------------|
| `API_TOKEN` | — | **Required.** Bearer token for all `/v1/*` requests. Generate with `openssl rand -hex 32`. |
| `DEBUG` | `false` | Set to `true` to enable DEBUG-level console logging |
| `PORT` | `8000` | Port the server listens on (local dev) |

> On Render, set env vars in **Dashboard → Service → Environment**.

---

## Authentication

All `/v1/*` endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <API_TOKEN>
```

Missing or incorrect token returns `401 Unauthorized`. `/health` is public.

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

**Errors**

| Status | Reason |
|--------|--------|
| `401` | Missing or invalid `Authorization: Bearer` header |
| `422` | Invalid request body |

### `GET /health`

Returns `{"status": "ok"}`. No auth required.

---

## Project structure

```
src/not_your_it_guy/
├── main.py          # App entry point, logging config
├── models.py        # Pydantic request/response models
├── auth.py          # Bearer token auth dependency
└── routers/
    └── responses.py # POST /v1/responses handler
```
