# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start PostgreSQL (required before running the API)
docker compose up -d

# Install Python dependencies (first time or after dependency changes)
python -m pip install -e ".[dev]"
# psycopg2-binary is included; no extra install needed for PostgreSQL support

# Run the API
uvicorn app.main:app --reload

# API docs (requires running API)
# Swagger UI  → http://localhost:8000/docs
# ReDoc       → http://localhost:8000/redoc
# OpenAPI JSON→ http://localhost:8000/openapi.json

# Run the Next.js frontend (separate terminal)
cd frontend && npm install && npm run dev
# UI → http://localhost:3000

# Run all tests
python -m pytest

# Run a single test
python -m pytest tests/test_health.py::test_health_status_code -v

# Run tests with output
python -m pytest -s -v
```

On Windows, use `python -m pip install -e ".[dev]" --user` if you hit permission errors.

## Architecture

BridgeAI follows **Clean Architecture** with a strict dependency rule: outer layers depend on inner layers, never the reverse.

```
domain/          ← innermost: pure Python dataclasses, no framework imports
services/        ← business logic, depends only on domain/
repositories/    ← data access abstractions (to be implemented per feature)
api/routes/      ← FastAPI routers, depend on services via DI
database/        ← SQLAlchemy infrastructure, injected via get_db()
core/            ← cross-cutting: config, logging middleware, security middleware
```

### Key patterns

**Settings** (`app/core/config.py`) — single `Settings` class via `pydantic-settings`, cached with `@lru_cache`. Always inject via `get_settings()`, never instantiate directly. Switching from SQLite to PostgreSQL requires only changing `DATABASE_URL` in `.env`.

**App factory** (`app/main.py`) — `create_app()` returns a configured `FastAPI` instance. Use this factory in tests (`TestClient(create_app())`). Middleware order is intentional: CORS → Security → Logging.

**Database** (`app/database/session.py`) — `Base` (DeclarativeBase) lives here; all ORM models must inherit from it so `init_db()` picks them up automatically. Use `get_db()` as a FastAPI dependency for route handlers; use `check_db_connection()` for health checks only.

**Domain objects** (`app/domain/`) — frozen dataclasses with no SQLAlchemy or FastAPI imports. Key entities: `FileInfo`, `RequirementUnderstanding`, `UserStory`, `TicketResult`, `TicketIntegration`.

**Services** (`app/services/`) — accept `Settings` via constructor injection (default: `get_settings()`). Ticket providers live in `app/services/ticket_providers/` and follow the `TicketProvider` ABC — `JiraTicketProvider` and `AzureDevOpsTicketProvider` are the two implementations.

**Ticket integration** (`app/services/ticket_integration_service.py`) — orchestrates idempotency check, payload build (for audit), provider call with exponential-backoff retry, and audit log persistence. Supports `jira` and `azure_devops` integration types.

**Logging** (`app/core/logging.py`) — `RequestLoggingMiddleware` attaches a `request_id` UUID to `request.state` on every request. Access it in route handlers via `request.state.request_id`. Use `get_logger(__name__)` everywhere else.

### Adding a new feature

1. Define domain objects in `app/domain/`.
2. Implement business logic as a service in `app/services/`.
3. Add a repository in `app/repositories/` if persistence is needed (inject `Session` via `get_db()`).
4. Create a router in `app/api/routes/` and register it in `create_app()`.
5. Add tests under `tests/`; use `TestClient(create_app())` as the fixture.

## Configuration

Copy `.env.example` to `.env` before running. Relevant variables:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./app.db` | Switch to `postgresql://...` for production |
| `PROJECT_ROOT` | `.` | Root path scanned by `CodeScanner` |
| `LOG_LEVEL` | `INFO` | Standard Python logging level |
| `DRY_RUN` | `false` | Prevents side-effects in future write operations |
| `AI_PROVIDER` | `stub` | `stub` \| `anthropic` \| `openai` |
| `ANTHROPIC_API_KEY` | — | Required when `AI_PROVIDER=anthropic` |
| `JIRA_BASE_URL` | — | e.g. `https://your-org.atlassian.net` |
| `JIRA_USER_EMAIL` | — | Jira account email |
| `JIRA_API_TOKEN` | — | Jira API token (generate at id.atlassian.com) |
| `JIRA_ISSUE_TYPE_MAP` | — | e.g. `Story=Historia,Task=Tarea` for non-English projects |
| `AZURE_DEVOPS_TOKEN` | — | Azure DevOps Personal Access Token |
| `AZURE_ORG_URL` | — | e.g. `https://dev.azure.com/your-org` |
| `AZURE_PROJECT` | — | Azure DevOps project name |

Frontend env — create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Development agents (`.claude/agents/`)

Specialized Claude Code roles for common development tasks:

| Agent | When to invoke |
|---|---|
| `clean-arch-guardian` | Review any new/modified `app/` file for layer violations |
| `domain-modeler` | Create a new frozen dataclass in `app/domain/` |
| `api-route-builder` | Scaffold a full vertical slice (domain → service → route → test) |
| `test-specialist` | Write or expand tests for any layer |
| `phase-implementer` | Implement an entire roadmap phase end-to-end |
| `nextjs-frontend-builder` | Build, extend, or fix any part of the Next.js frontend in `frontend/` |

## Roadmap phases — status

| Phase | Feature | Status |
|---|---|---|
| 1 | Code Indexing | Done |
| 2 | Impact Analysis | Done |
| 3 | Requirement Understanding (LLM) | Done |
| 4 | Story Generation | Done |
| 5a | Jira integration — provider pattern, idempotency, audit log | Done |
| 5b | Hardening — exponential backoff, Retry-After, full audit payload | Done |
| 5c | Azure DevOps integration | Done |
| 6 | Next.js frontend (replaces Streamlit) | Done |
