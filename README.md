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
| Database | PostgreSQL (Alembic migrations, SQLAlchemy async) |
| Logging | [Loguru](https://loguru.readthedocs.io/) |
| Container | Docker (multi-stage, `python:3.12-slim`) |
| Local DB | Docker Compose |

---

## Local development

### Prerequisites

- Python 3.12 (via `pyenv` or system install)
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- Docker + Docker Compose

### Setup

```bash
git clone <repo-url>
cd not-your-it-guy

cp .env.example .env   # fill in API_TOKEN, OPENAI_API_KEY, DATABASE_URL
uv sync                # creates .venv and installs deps
```

### Run with Docker Compose (recommended)

Starts Postgres + the app together. Migrations run automatically on startup.

```bash
docker compose up --build
```

### Run app locally (DB in Docker only)

```bash
docker compose up db -d   # start Postgres only
uv run serve              # start app locally, connects to localhost:5432
```

On startup you should see:
```
Starting Not Your IT Guy — log level: DEBUG
API_TOKEN loaded: yes
Migrations applied.
Async DB engine initialised.
```

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

The `email` field in metadata is the employee's **private/personal email**. Corporate email is derived automatically as `name.surname@b2.com`.

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

### Verify DB record

```bash
docker compose exec db psql -U mssvcacc -d msmock
```

```sql
SELECT id, name, surname, corporate_email, private_email, department, created_at FROM employees;
```

### Fallback (unrecognised intent)

```bash
curl -s -X POST http://localhost:8000/v1/responses \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","input":"what is the weather today","stream":false}' | jq
```

---

## Employee onboarding flow

When an onboarding request is received:

1. **Router** classifies intent as `employee_onboarding` (keyword pre-filter + `gpt-4o-mini` for param extraction)
2. **Subgraph** invokes two steps: `handle` → `create_ad_user`
3. **Mock AD / Entra ID** (`entra_id_mock_service`):
   - Derives corporate email: `name.surname@b2.com`
   - Generates a 12-character random temporary password
   - Stores SHA-256 hash of the password in the `employees` table
   - Inserts: `name`, `surname`, `corporate_email`, `private_email`, `phone`, `department`, `line_manager`
4. **SMS** (`sms_service` → `twilio_sms_tool`): sends temporary password via Twilio SMS — logs to console if `TWILIO_*` vars not set
5. **Welcome email** (`welcome_email_service` → `sendgrid_email_tool`): sends welcome email to private inbox via SendGrid — logs to console if `SENDGRID_API_KEY` not set

### SMS mock log example

```
[sms_service] TWILIO not configured — temporary password for B2 account sent to +1 555 123 4567: aB3!kX9mQz1#
```

### Welcome email content (sent to private inbox)

Delivered via SendGrid. Falls back to console log if `SENDGRID_API_KEY` is not set.

```
  >> JESSICA
  >> YOUR AI IT ADMIN
  >> B2 CORP

Hey John,

Account provisioned. You're in.

  CORP EMAIL    : john.doe@b2.com
  TEMP PASSWORD : sent via SMS to +1 555 123 4567

[!] Change your password on first login.

Access your tools:
  - Microsoft Mailbox : https://outlook.cloud.microsoft/
  - Notion            : https://www.notion.so/ (invite sent to corporate email)
  - Microsoft Teams   : https://teams.microsoft.com/

I'll be around if you need anything. Just ask.
— Jessica, your AI IT Admin
```

---

## Database

### Schema — `employees` table

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial PK | Auto-increment |
| `name` | varchar(100) | First name |
| `surname` | varchar(100) | Last name |
| `email` | varchar(255) unique | Corporate email (backwards compat) |
| `corporate_email` | varchar(255) unique | Derived: `name.surname@b2.com` |
| `private_email` | varchar(255) | Personal inbox (from request metadata) |
| `temp_password_hash` | varchar(255) | SHA-256 hash of generated temp password |
| `phone` | varchar(50) | Mobile — used for SMS delivery |
| `department` | varchar(100) | Department |
| `line_manager` | varchar(100) | Line manager full name |
| `created_at` | timestamptz | Auto-set on insert |

### Migrations

Migrations run automatically on app startup via Alembic. To run manually:

```bash
uv run alembic upgrade head
```

---

## Docker Compose

```yaml
services:
  db:   # Postgres 16, port 5432
  app:  # FastAPI app, port 8000 — waits for db healthcheck before starting
```

Local DB credentials (set in `.env`):
```
DATABASE_URL=postgresql://mssvcacc:nyig_local@db:5432/msmock
DB_PASSWORD=nyig_local
```

---

## Docker (standalone)

### Build

```bash
docker build -t not-your-it-guy:dev .
```

### Run

```bash
docker run --rm -p 8000:8000 --env-file .env not-your-it-guy:dev
```

---

## Deploy to Render

1. Push to GitHub
2. Create a **Web Service** pointing to the repo
3. Set environment variables in **Dashboard → Service → Environment**:

| Variable | Value |
|----------|-------|
| `API_TOKEN` | generate with `openssl rand -hex 32` |
| `OPENAI_API_KEY` | your OpenAI key |
| `DATABASE_URL` | Internal Database URL from Render Postgres dashboard |
| `AUTH_USERNAME` | frontend basic auth username |
| `AUTH_PASSWORD` | frontend basic auth password |
| `DEBUG` | `false` (or `true` for verbose logs) |
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_FROM_NUMBER` | Twilio sender number (E.164, e.g. `+19047204944`) |
| `SENDGRID_API_KEY` | SendGrid API key |
| `SENDGRID_FROM_EMAIL` | Verified sender address |

Migrations run automatically on every deploy.

---

## Configuration

All config via environment variables. Copy `.env.example` to `.env` for local development.

| Variable | Default | Description |
|----------|---------|-------------|
| `API_TOKEN` | — | **Required.** Bearer token for all `/v1/*` requests |
| `OPENAI_API_KEY` | — | **Required.** Used by the semantic router |
| `DATABASE_URL` | — | **Required.** PostgreSQL connection string |
| `DB_PASSWORD` | `nyig_local` | Docker Compose local DB password |
| `AUTH_USERNAME` | `admin` | HTTP Basic Auth username for frontend |
| `AUTH_PASSWORD` | `changeme` | HTTP Basic Auth password for frontend |
| `DEBUG` | `false` | Enable DEBUG-level logging |
| `PORT` | `8000` | Server port |
| `SENDGRID_API_KEY` | — | SendGrid API key — welcome emails logged to console if not set |
| `SENDGRID_FROM_EMAIL` | — | Verified sender address (single sender or domain auth) |
| `TWILIO_ACCOUNT_SID` | — | Twilio account SID — SMS logged to console if not set |
| `TWILIO_AUTH_TOKEN` | — | Twilio auth token |
| `TWILIO_FROM_NUMBER` | — | Twilio sender number (E.164 format, e.g. `+14155552671`) |

---

## Authentication

All `/v1/*` endpoints require a Bearer token:

```
Authorization: Bearer <API_TOKEN>
```

Missing or incorrect token → `401 Unauthorized`. `/health` is public.

Frontend (`GET /`, `GET /v2`) is protected by HTTP Basic Auth.

---

## How routing works

1. Request arrives at `POST /v1/responses`
2. **Stage 1:** keyword pre-filter checks for known intent keywords (no API call)
3. **Stage 2:** `gpt-4o-mini` classifies intent and extracts structured params as JSON
4. The detected intent is looked up in `subgraph_factory`
5. The matching LangGraph subgraph is invoked and its output is streamed back
6. If no intent matches → fallback message is returned

---

## API

### `POST /v1/responses`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | yes | Model name (passed through) |
| `input` | string or message list | yes | User message |
| `stream` | boolean | no | `true` for SSE, `false` for JSON (default) |
| `metadata` | object | no | Employee fields passed to the subgraph |

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
├── main.py                          # App entry point, logging, DB setup
├── models.py                        # Pydantic request/response + SSE event models
├── auth.py                          # Bearer token auth dependency
├── logger/
│   └── logger_provider.py           # Loguru setup + stdlib bridge
├── db/
│   ├── models.py                    # SQLAlchemy ORM models
│   └── session.py                   # Async engine + session factory
├── routers/
│   └── responses.py                 # POST /v1/responses — streaming + non-streaming
├── services/
│   ├── router_service.py            # LLM-based intent classification
│   ├── subgraph_factory.py          # Registry of available subgraphs
│   ├── entra_id_mock_service.py     # Mock AD: corporate email derivation, password gen, DB insert
│   ├── sms_service.py               # SMS mock (Twilio stub) — sends temp password
│   └── welcome_email_service.py     # Welcome email via SendGrid — sends to private inbox
├── subgraphs/
│   └── employee_onboarding.py       # Employee onboarding LangGraph subgraph
└── tools/
    ├── ad_user_tool.py              # LangChain @tool wrapping entra_id_mock_service
    ├── twilio_sms_tool.py           # Twilio SMS via LangChain TwilioAPIWrapper
    └── sendgrid_email_tool.py       # SendGrid email via SendGrid Python SDK

src/migrations/
├── env.py
└── versions/
    ├── 0001_create_employees.py
    └── 0002_add_private_email_and_password_hash.py

frontend/
├── index.html                       # GET / — cyberpunk UI with ElevenLabs agent v1
└── v2/
    └── index.html                   # GET /v2 — Jessica, your AI IT Admin
```
