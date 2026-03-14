# not-your-it-guy

OpenAI-compatible agent backend. Accepts requests on the [Responses API](https://platform.openai.com/docs/api-reference/responses) format so any off-the-shelf OpenAI client works out of the box.

Incoming requests are classified by an LLM-based semantic router and dispatched to the matching LangGraph subgraph.

**Deployed:** `https://not-your-it-guy.onrender.com`

---

## Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.12 |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Web framework | FastAPI + Uvicorn |
| Agent framework | LangGraph |
| Intent classification | OpenAI `gpt-4o-mini` |
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

cp .env.example .env   # fill in API_TOKEN and OPENAI_API_KEY

uv sync                # creates .venv and installs deps
```

### Run

```bash
cd not-your-it-guy  # must run from project root so .env is found
uv run uvicorn not_your_it_guy.main:app --host 0.0.0.0 --port 8000 --reload
```

On startup you should see:
```
API_TOKEN loaded: yes
```

If you see `NO — auth will reject all requests`, the `.env` file is not being picked up.

---

## Testing

### Health check (no auth)

```bash
curl http://localhost:8000/health
```

### Employee onboarding — non-streaming

```bash
curl -s -X POST http://localhost:8000/v1/responses \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "stream": false,
    "input": "help me onboard a new employee",
    "metadata": {
      "name": "John",
      "surname": "Doe",
      "email": "john.doe@company.com",
      "phone": "+1 555 123 4567",
      "department": "Engineering",
      "line_manager": "Jane Smith"
    }
  }' | jq
```

### Employee onboarding — streaming (SSE)

```bash
curl -s -X POST http://localhost:8000/v1/responses \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "stream": true,
    "input": "help me onboard a new employee",
    "metadata": {
      "name": "John",
      "surname": "Doe",
      "email": "john.doe@company.com",
      "phone": "+1 555 123 4567",
      "department": "Engineering",
      "line_manager": "Jane Smith"
    }
  }'
```

Streaming returns Server-Sent Events in this order:
1. `response.created` — response object created
2. `response.output_text.delta` × N — one event per token/chunk
3. `response.output_text.done` — full assembled text
4. `response.completed` — final response object

### Fallback (unrecognised intent)

```bash
curl -s -X POST http://localhost:8000/v1/responses \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","input":"what is the weather today","stream":false}' | jq
```

Returns a fallback message when no subgraph matches the intent.

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

---

## Deployed on Render

```bash
# Health check
curl https://not-your-it-guy.onrender.com/health

# Employee onboarding
curl -s -X POST https://not-your-it-guy.onrender.com/v1/responses \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "stream": false,
    "input": "help me onboard a new employee",
    "metadata": {
      "name": "John",
      "surname": "Doe",
      "email": "john.doe@company.com",
      "phone": "+1 555 123 4567",
      "department": "Engineering",
      "line_manager": "Jane Smith"
    }
  }' | jq
```

---

## Configuration

All config is via environment variables. Copy `.env.example` to `.env` for local development.

| Variable | Default | Description |
|----------|---------|-------------|
| `API_TOKEN` | — | **Required.** Bearer token for all `/v1/*` requests. Generate with `openssl rand -hex 32`. |
| `OPENAI_API_KEY` | — | **Required.** Used by the semantic router (`gpt-4o-mini`) and subgraphs. |
| `DEBUG` | `false` | Set to `true` to enable DEBUG-level console logging |
| `PORT` | `8000` | Port the server listens on (local dev) |

> On Render, set env vars in **Dashboard → Service → Environment**.

---

## Authentication

All `/v1/*` endpoints require a Bearer token:

```
Authorization: Bearer <API_TOKEN>
```

Missing or incorrect token → `401 Unauthorized`. `/health` is public.

---

## How routing works

1. Request arrives at `POST /v1/responses`
2. `router_service` sends the input to `gpt-4o-mini` for intent classification
3. The detected intent (e.g. `employee_onboarding`) is looked up in `subgraph_factory`
4. The matching LangGraph subgraph is invoked and its output is streamed back
5. If no intent matches → fallback message is returned

---

## API

### `POST /v1/responses`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | yes | Model name (passed through, routing uses `gpt-4o-mini`) |
| `input` | string or message list | yes | User message |
| `stream` | boolean | no | `true` for SSE streaming, `false` for JSON (default) |
| `metadata` | object | no | Arbitrary key/value pairs passed to the subgraph |

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
├── main.py                        # App entry point, logging config
├── models.py                      # Pydantic request/response + SSE event models
├── auth.py                        # Bearer token auth dependency
├── routers/
│   └── responses.py               # POST /v1/responses — streaming + non-streaming
├── services/
│   ├── router_service.py          # LLM-based intent classification (gpt-4o-mini)
│   └── subgraph_factory.py        # Registry of available subgraphs
├── subgraphs/
│   └── employee_onboarding.py     # Employee onboarding LangGraph subgraph (stub)
└── tools/                         # LangGraph tools and MCP integrations (future)
```
