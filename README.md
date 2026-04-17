# BridgeAI

AI-powered requirement-to-ticket automation. Paste a requirement, get a complete User Story with acceptance criteria, impact analysis, and a Jira or Azure DevOps ticket — in seconds.

## Quick Start

```bash
# 1. Install Python dependencies
pip install -e ".[dev]"

# 2. Configure environment
cp .env.example .env
# Edit .env with your AI provider key and Jira/Azure DevOps credentials

# 3. Run the API  (terminal 1)
uvicorn app.main:app --reload
# API → http://localhost:8000
# Docs → http://localhost:8000/docs

# 4. Run the frontend  (terminal 2)
cd frontend
npm install
npm run dev
# UI → http://localhost:3000

# 5. Run tests
pytest
```

## User Flow

1. **Index** your codebase (`/indexing` page or `POST /api/v1/index`)
2. **Understand** a requirement — extracts intent, complexity, keywords
3. **Analyze impact** — identifies affected files/modules and risk level
4. **Generate story** — produces title, description, acceptance criteria, tasks, DoD, story points
5. **Create ticket** — pushes to Jira or Azure DevOps with a single click

## Project Structure

```
app/
├── api/routes/          # FastAPI routers
├── core/                # Config, logging, security middleware
├── database/            # SQLAlchemy engine & session factory
├── domain/              # Pure domain models (frozen dataclasses, no framework deps)
├── services/            # Business logic
│   └── ticket_providers/  # TicketProvider ABC → JiraTicketProvider, AzureDevOpsTicketProvider
├── repositories/        # Data access layer
├── models/              # ORM models
└── utils/               # Shared utilities
frontend/                # Next.js 15 + TypeScript + Tailwind + shadcn/ui
tests/                   # pytest test suite
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | API + DB health |
| POST | `/api/v1/index` | Index codebase |
| POST | `/api/v1/understand-requirement` | Parse requirement with LLM |
| POST | `/api/v1/impact-analysis` | Assess code impact |
| POST | `/api/v1/generate-story` | Generate User Story |
| GET | `/api/v1/stories/{story_id}` | Fetch full story detail |
| POST | `/api/v1/tickets` | Create Jira or Azure DevOps ticket |
| GET | `/api/v1/tickets/{story_id}` | Get ticket status |
| GET | `/api/v1/tickets/{story_id}/audit` | Audit log for a ticket |
| GET | `/api/v1/integration/health` | Check Jira + Azure DevOps connectivity |

## Configuration

Key `.env` variables:

```bash
# AI
AI_PROVIDER=anthropic          # stub | anthropic | openai
ANTHROPIC_API_KEY=sk-ant-...

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

Frontend (`frontend/.env.local`):

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Architecture

Clean Architecture — dependency rule strictly enforced: outer layers depend on inner, never the reverse.

```
domain → services → repositories → api/routes
```

See `CLAUDE.md` for full architecture notes and development agent guide.
