# BridgeAI

AI-powered requirement-to-ticket automation. Paste a requirement, get a complete User Story with acceptance criteria, impact analysis, and a Jira or Azure DevOps ticket — in seconds.

## Quick Start

```bash
# 1. Start PostgreSQL
docker compose up -d

# 2. Install Python dependencies
pip install -e ".[dev]"

# 3. Configure environment
cp .env.example .env
# Edit .env — minimum required: DATABASE_URL, AI_PROVIDER (or leave as "stub")

# 4. Run DB migrations
python -m alembic upgrade head

# 5. Run the API  (terminal 1)
uvicorn app.main:app --reload
# API  → http://localhost:8000
# Docs → http://localhost:8000/docs

# 6. Run the frontend  (terminal 2)
cd frontend
npm install
npm run dev
# UI → http://localhost:3000

# 7. Run tests
python -m pytest
```

## User Flow

1. **Connect** a source code repository (GitHub, GitLab, Azure Repos, Bitbucket) via `/connections`
2. **Index** the active repository — files are stored per-connection, never mixed
3. **Understand** a requirement — extracts intent, complexity, keywords
4. **Analyze impact** — identifies affected files/modules and risk level
5. **Generate story** — produces title, description, acceptance criteria, tasks, DoD, story points
6. **Create ticket** — pushes to Jira or Azure DevOps with a single click

## Project Structure

```
app/
├── api/routes/          # FastAPI routers
├── core/                # Config, logging, auth0 auth, security middleware, tenant context
├── database/            # SQLAlchemy engine & session factory
├── domain/              # Pure domain models (frozen dataclasses, no framework deps)
├── services/            # Business logic
│   ├── scm_providers/   # ScmProvider ABC → GitHub, GitLab, Azure Repos, Bitbucket
│   └── ticket_providers/# TicketProvider ABC → JiraTicketProvider, AzureDevOpsTicketProvider
├── repositories/        # Data access layer (all queries scoped by tenant_id)
├── models/              # ORM models
└── core/context.py      # ContextVar-based tenant isolation
frontend/                # Next.js 16 + TypeScript + Tailwind + shadcn/ui
alembic/                 # DB migrations
tests/                   # pytest suite (unit + integration + e2e)
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | API + DB health |
| POST | `/api/v1/auth/provision` | Create/sync user and tenant on first login |
| POST | `/api/v1/index` | Index active repository (remote or local) |
| GET | `/api/v1/index/status` | File count and last indexed timestamp for active repo |
| POST | `/api/v1/understand-requirement` | Parse requirement with LLM |
| POST | `/api/v1/impact-analysis` | Assess code impact on indexed codebase |
| GET | `/api/v1/impact-analysis/{id}/files` | Paginated list of impacted files |
| POST | `/api/v1/generate-story` | Generate User Story |
| GET | `/api/v1/stories/{story_id}` | Fetch full story detail |
| POST | `/api/v1/tickets` | Create Jira or Azure DevOps ticket |
| GET | `/api/v1/tickets/{story_id}` | Get ticket status |
| GET | `/api/v1/tickets/{story_id}/audit` | Audit log for a ticket |
| GET | `/api/v1/connections` | List SCM connections for current tenant |
| GET | `/api/v1/connections/active` | Get the active repository connection |
| POST | `/api/v1/connections/{id}/activate` | Set a connection + repo as active |
| GET | `/api/v1/connections/oauth/authorize/{platform}` | Start OAuth flow |
| GET | `/api/v1/connections/oauth/callback/{platform}` | OAuth callback |
| DELETE | `/api/v1/connections/{id}` | Remove a connection |

## Configuration

### Backend — `.env`

```bash
# Database
DATABASE_URL=postgresql://bridgeai:bridgeai@localhost:5432/bridgeai

# AI provider
AI_PROVIDER=anthropic          # stub | anthropic | openai
ANTHROPIC_API_KEY=sk-ant-...

# Auth0 (backend JWT validation)
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_AUDIENCE=https://your-api-audience

# Jira
JIRA_BASE_URL=https://your-org.atlassian.net
JIRA_USER_EMAIL=you@company.com
JIRA_API_TOKEN=your_token
JIRA_ISSUE_TYPE_MAP=Story=Historia,Task=Tarea,Bug=Error   # for non-English projects

# Azure DevOps
AZURE_DEVOPS_TOKEN=your_pat
AZURE_ORG_URL=https://dev.azure.com/your-org
AZURE_PROJECT=your-project
```

### Frontend — `frontend/.env.local`

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000

# Auth0 (Next.js SDK)
AUTH0_SECRET=a-long-random-secret-min-32-chars
AUTH0_BASE_URL=http://localhost:3000
AUTH0_ISSUER_BASE_URL=https://your-tenant.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH0_AUDIENCE=https://your-api-audience
```

## Architecture

Clean Architecture — dependency rule strictly enforced: outer layers depend on inner, never the reverse.

```
domain → services → repositories → api/routes
```

**Multi-tenancy**: every request sets `current_tenant_id` via `ContextVar` in `app/core/auth0_auth.py`. All repositories filter by `_tid()` automatically — no cross-tenant data leakage is possible at the query layer.

**Repository isolation**: indexed files are scoped by `source_connection_id`. Switching repositories never mixes files from different repos. Impact analysis always runs against the active connection's files only.

See `CLAUDE.md` for full architecture notes and development agent guide.
