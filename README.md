# BridgeAI

AI-powered code analysis and User Story generation — MVP Foundation.

## Quick Start

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Copy env file
cp .env.example .env

# 3. Run the API
uvicorn app.main:app --reload

# 4. Run the UI (separate terminal)
streamlit run ui/app.py

# 5. Run tests
pytest
```

## Structure

```
app/
├── api/routes/      # FastAPI routers
├── core/            # Config, logging, security middleware
├── database/        # SQLAlchemy engine & session factory
├── domain/          # Pure domain models (no framework deps)
├── services/        # Business logic (CodeScanner, etc.)
├── repositories/    # Data access layer
├── models/          # ORM models
└── utils/           # Shared utilities
ui/
└── app.py           # Streamlit demo
tests/               # pytest test suite
```

## Roadmap

- Phase 1 — Code Indexing
- Phase 2 — Impact Analysis
- Phase 3 — Requirement Understanding
- Phase 4 — Story Generation
- Phase 5 — Jira / Azure DevOps Integration
