# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start PostgreSQL (required before running the API)
docker compose up -d

# Install Python dependencies (first time or after dependency changes)
python -m pip install -e ".[dev]"
# psycopg2-binary is included; no extra install needed for PostgreSQL support

# Run DB migrations (required after first install or after pulling new migrations)
python -m alembic upgrade head

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
core/            ← cross-cutting: config, logging middleware, security middleware, tenant context
```

### Key patterns

**Settings** (`app/core/config.py`) — single `Settings` class via `pydantic-settings`, cached with `@lru_cache`. Always inject via `get_settings()`, never instantiate directly. Database is PostgreSQL only; configure `DATABASE_URL` in `.env`.

**App factory** (`app/main.py`) — `create_app()` returns a configured `FastAPI` instance. Use this factory in tests (`TestClient(create_app())`). Middleware order is intentional: CORS → Security → Logging.

**Database** (`app/database/session.py`) — `Base` (DeclarativeBase) lives here; all ORM models must inherit from it so `init_db()` picks them up automatically. Use `get_db()` as a FastAPI dependency for route handlers; use `check_db_connection()` for health checks only.

**Domain objects** (`app/domain/`) — frozen dataclasses with no SQLAlchemy or FastAPI imports. Key entities: `FileInfo`, `RequirementUnderstanding`, `UserStory`, `TicketResult`, `TicketIntegration`, `CoherenceResult`.

**Services** (`app/services/`) — accept `Settings` via constructor injection (default: `get_settings()`). Ticket providers live in `app/services/ticket_providers/` and follow the `TicketProvider` ABC — `JiraTicketProvider` and `AzureDevOpsTicketProvider` are the two implementations. SCM providers live in `app/services/scm_providers/` and follow the `ScmProvider` ABC — GitHub, GitLab, Azure Repos, and Bitbucket implementations exist.

**Ticket integration** (`app/services/ticket_integration_service.py`) — orchestrates idempotency check, payload build (for audit), provider call with exponential-backoff retry, and audit log persistence. Supports `jira` and `azure_devops` integration types.

**Authentication** (`app/core/auth0_auth.py`) — Auth0 JWT validation via JWKS (cached 1 hour). `get_current_user()` FastAPI dependency verifies the bearer token, loads the `User` record, and sets `current_tenant_id` + `current_user_id` in `ContextVar`. Every route that touches a repository must declare `_user: User = Depends(get_current_user)`.

**Tenant context** (`app/core/context.py`) — `ContextVar`-based isolation. `get_tenant_id()` raises `RuntimeError` if the context is not set, making missing auth hard to miss. All repositories call `_tid()` which delegates to `get_tenant_id()` — no cross-tenant query is possible at the data layer.

**Repository isolation** (`app/models/code_file.py`) — `CodeFile` has a `source_connection_id` FK scoping files to a specific SCM connection. The unique constraint is `(tenant_id, source_connection_id, file_path)`. All `CodeFileRepository` methods accept an optional `source_connection_id` to filter to a single repo. `ImpactAnalysisService` resolves the active connection before iterating files, so analysis never mixes repos. This means:
- Two different users never see each other's files.
- A single user switching repos never gets cross-repo contamination in analysis or status counts.

**Logging** (`app/core/logging.py`) — `RequestLoggingMiddleware` attaches a `request_id` UUID to `request.state` on every request. Access it in route handlers via `request.state.request_id`. Use `get_logger(__name__)` everywhere else.

**Coherence pre-filter** (`app/services/requirement_coherence_validator.py`, `app/services/requirement_gibberish_filter.py`) — 3-layer input gate that runs inside `RequirementUnderstandingService.understand()` **before** the cache lookup, so rejected text is never stored as a valid requirement:
1. **Gibberish filter** (deterministic, no LLM cost) — rejects random character sequences (`sddssdd`, `fghfgh`).
2. **Coherence validator** (LLM) — `RequirementCoherenceValidator` ABC; factory `get_coherence_validator(settings)` picks the right implementation (`anthropic`, `openai`, `groq`, `gemini`, or `stub`). Raises `IncoherentRequirementError` on rejection. **Fail-open**: network/timeout errors skip the gate rather than blocking the user.
3. **Invalid-intent fallback** — if the main parser returns `intent="invalid_requirement"`, it is also rejected here.

Rejected requirements are persisted to `incoherent_requirements` table via `IncoherentRequirementRepository`. The admin endpoint `GET /api/v1/admin/incoherent-requirements` (role `admin` only) returns a paginated list filterable by `reason` code. Valid reason codes: `non_software_request`, `contradictory`, `unintelligible`, `conversational`, `empty_intent`.

Controlled by `COHERENCE_VALIDATION_ENABLED` (default `true`). Reuses `AI_JUDGE_PROVIDER`/`AI_JUDGE_MODEL` settings (falls back to `AI_PROVIDER`/`AI_MODEL`).

**Quality metrics partitioning** — `user_stories.entity_not_found` is the partition key for all aggregate judge metrics. When `True`, the requirement's main entity wasn't in the codebase and the judge applies hard score caps by design (`story_quality_judge.py`). `StoryQualityRepository.summary_since()` and `GET /api/v1/system/quality/live` separate **organic** (`entity_not_found=False`) from **forced** (`entity_not_found=True`) buckets so degraded-input runs don't pollute the baseline. The legacy `GET /api/v1/system/quality` keeps reading `eval_report.json` from the offline harness — leave it alone for batch eval.

### Adding a new feature

1. Define domain objects in `app/domain/`.
2. Implement business logic as a service in `app/services/`.
3. Add a repository in `app/repositories/` if persistence is needed (inject `Session` via `get_db()`). Every repository must implement `_tid()` calling `get_tenant_id()`.
4. Create a router in `app/api/routes/` and register it in `create_app()`. Every route accessing tenant data must declare `_user: User = Depends(get_current_user)`.
5. Add tests under `tests/`; use `TestClient(create_app())` as the fixture.
6. If the feature adds new tables, create an Alembic migration: `python -m alembic revision --autogenerate -m "description"` then `python -m alembic upgrade head`.

## Configuration

Copy `.env.example` to `.env` before running. Relevant variables:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql://bridgeai:bridgeai@localhost:5432/bridgeai` | PostgreSQL connection string |
| `PROJECT_ROOT` | `.` | Root path scanned by local `CodeIndexingService` |
| `LOG_LEVEL` | `INFO` | Standard Python logging level |
| `DRY_RUN` | `false` | Prevents side-effects in future write operations |
| `AI_PROVIDER` | `stub` | `stub` \| `anthropic` \| `openai` |
| `ANTHROPIC_API_KEY` | — | Required when `AI_PROVIDER=anthropic` |
| `AUTH0_DOMAIN` | — | e.g. `your-tenant.auth0.com` |
| `AUTH0_AUDIENCE` | — | API audience configured in Auth0 dashboard |
| `JIRA_BASE_URL` | — | e.g. `https://your-org.atlassian.net` |
| `JIRA_USER_EMAIL` | — | Jira account email |
| `JIRA_API_TOKEN` | — | Jira API token (generate at id.atlassian.com) |
| `JIRA_ISSUE_TYPE_MAP` | — | e.g. `Story=Historia,Task=Tarea` for non-English projects |
| `AZURE_DEVOPS_TOKEN` | — | Azure DevOps Personal Access Token |
| `AZURE_ORG_URL` | — | e.g. `https://dev.azure.com/your-org` |
| `AZURE_PROJECT` | — | Azure DevOps project name |
| `COHERENCE_VALIDATION_ENABLED` | `true` | Enable/disable the coherence pre-filter gate |
| `AI_COHERENCE_MAX_TOKENS` | `200` | Max tokens for the coherence validator LLM call |

Frontend env — create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000

AUTH0_SECRET=a-long-random-secret-at-least-32-chars
AUTH0_BASE_URL=http://localhost:3000
AUTH0_ISSUER_BASE_URL=https://your-tenant.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH0_AUDIENCE=https://your-api-audience
```

## Development agents (`.claude/agents/`)

Specialized Claude Code roles for common development tasks:

| Agent | When to invoke |
|---|---|
| `clean-arch-guardian` | Review any new/modified `app/` file for layer violations |
| `clean-arch-guardian` | Review any new/modified `app/` file for layer violations |
| `domain-modeler` | Create a new frozen dataclass in `app/domain/` |
| `api-route-builder` | Scaffold a full vertical slice (domain → service → route → test) |
| `test-specialist` | Write or expand tests for any layer |
| `phase-implementer` | Implement an entire roadmap phase end-to-end |
| `nextjs-frontend-builder` | Build, extend, or fix any part of the Next.js frontend in `frontend/` |
| `security-guardian` | Audit, find, and fix security vulnerabilities; apply current best practices |

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
| 6 | Next.js 16 frontend — Auth0, multi-tenant, i18n, dark mode | Done |
| 7 | Repository isolation — per-connection file scoping, clean re-index | Done |
| 8 | Coherence pre-filter — gibberish gate, LLM coherence validator, incoherent-requirements audit log, admin endpoint | Done |
