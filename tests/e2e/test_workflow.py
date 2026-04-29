"""E2E happy-path test: full BridgeAI workflow via Chromium (Playwright).

All /api/v1/* calls are intercepted with page.route() so the test runs
without real auth tokens, Jira credentials, or AI providers.

REQUIREMENTS:
  Terminal 1: python -m uvicorn app.main:app --reload
  Terminal 2: cd frontend && npm run dev

RUN:
  pytest tests/e2e/test_workflow.py -v -s -m e2e
"""
import json
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright, Route, expect

FRONTEND = "http://localhost:3000"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"

REQ = (
    "As a registered user I want to reset my password via email "
    "so that I can recover my account if I forget my credentials."
)

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_CONN_GITHUB = {
    "id": "conn-gh-test",
    "platform": "github",
    "display_name": "Test GitHub",
    "repo_full_name": "test-org/test-repo",
    "default_branch": "main",
    "is_active": True,
    "created_at": "2024-01-01T00:00:00Z",
}

_CONN_JIRA = {
    "id": "conn-jira-test",
    "platform": "jira",
    "display_name": "Test Jira",
    # repo_full_name stores the Jira site URL — required for hasSite=true in Step1
    "repo_full_name": "https://test.atlassian.net",
    "is_active": True,
    "created_at": "2024-01-01T00:00:00Z",
}

_STORY_DETAIL = {
    "story_id": "story-test",
    "source_connection_id": "conn-gh-test",
    "requirement_id": "req-test",
    "impact_analysis_id": "analysis-test",
    "project_id": "test-org/test-repo",
    "title": "Password Reset via Email",
    "story_description": "As a registered user I can reset my password via email.",
    "acceptance_criteria": [
        "Given I am on the login page, when I click 'Forgot password', then I see an email form.",
        "Given I submit a valid email, then I receive a reset link within 5 minutes.",
    ],
    "subtasks": {
        "frontend": [
            {"title": "Add forgot-password link", "description": "Place a link on the login screen."},
            {"title": "Build reset-password form", "description": "Form receives the reset token from the URL."},
        ],
        "backend": [
            {"title": "Implement reset token generation", "description": "Tokens expire in 15 minutes."},
            {"title": "Send reset email", "description": "Email contains a single-use link with the token."},
        ],
        "configuration": [],
    },
    "definition_of_done": ["Unit tests pass", "E2E test covers happy path"],
    "risk_notes": ["Token expiry must be validated server-side"],
    "story_points": 5,
    "risk_level": "medium",
    "is_locked": False,
    "created_at": "2024-01-01T00:00:00Z",
    "generation_time_seconds": 1.0,
}

_QUALITY_METRICS = {
    "structural": {
        "schema_valid": True,
        "ac_count": 2,
        "risk_notes_count": 1,
        "subtask_count": 4,
        "cited_paths_total": 0,
        "cited_paths_existing": 0,
        "citation_grounding_ratio": 1.0,
    },
    "judge": None,
}


def _setup_routes(page) -> None:
    """Intercept all /api/v1/* requests and return deterministic stub data."""

    def handle(route: Route) -> None:
        url = route.request.url
        method = route.request.method

        def ok(body: object) -> None:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(body),
            )

        # Order matters: more-specific patterns first.
        if "/api/v1/connections/active" in url:
            ok(_CONN_GITHUB)

        elif "/jira-projects" in url:
            # Return empty list → Step4 shows a text input instead of a select
            ok([])

        elif "/api/v1/connections" in url and method == "GET":
            ok([_CONN_JIRA, _CONN_GITHUB])

        elif "/api/v1/index/status" in url:
            ok({"total_files": 150, "last_indexed_at": "2024-01-01T00:00:00Z"})

        elif "/api/v1/index" in url and method == "POST":
            ok({
                "files_indexed": 150,
                "files_scanned": 150,
                "files_updated": 0,
                "files_skipped": 0,
                "duration_seconds": 1.2,
                "source": "github",
                "repo_full_name": "test-org/test-repo",
            })

        elif "/api/v1/understand-requirement" in url:
            ok({
                "requirement_id": "req-test",
                "source_connection_id": "conn-gh-test",
                "intent": "account_recovery",
                "feature_type": "authentication",
                "estimated_complexity": "medium",
                "keywords": ["password", "email", "reset"],
            })

        elif "/api/v1/impact-analysis" in url:
            ok({
                "analysis_id": "analysis-test",
                "source_connection_id": "conn-gh-test",
                "files_impacted": 5,
                "modules_impacted": ["auth", "email"],
                "risk_level": "medium",
            })

        elif "/api/v1/generate-story" in url:
            ok({
                "story_id": "story-test",
                "source_connection_id": "conn-gh-test",
                "title": "Password Reset via Email",
                "story_points": 5,
                "risk_level": "medium",
                "generation_time_seconds": 1.0,
            })

        elif "/api/v1/stories/" in url and "/feedback" in url:
            if method == "GET":
                route.fulfill(status=200, content_type="application/json", body="null")
            else:
                ok({"id": "fb-test", "story_id": "story-test", "user_id": "user-test",
                    "rating": "thumbs_up", "comment": None,
                    "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"})

        elif "/api/v1/stories/" in url and "/quality" in url:
            ok(_QUALITY_METRICS)

        elif "/api/v1/stories/" in url:
            ok(_STORY_DETAIL)

        elif "/api/v1/tickets" in url and method == "POST":
            ok({
                "ticket_id": "TEST-123",
                "url": "https://test.atlassian.net/browse/TEST-123",
                "provider": "jira",
                "status": "created",
                "message": "Ticket created successfully",
            })

        else:
            route.continue_()

    page.route("**/api/v1/**", handle)


def _shot(page, name: str) -> None:
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  [SCREENSHOT] {name}.png")


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

@pytest.mark.e2e
@pytest.mark.slow
def test_full_workflow():
    SCREENSHOTS_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # Route mocks must be registered before the first navigation.
        _setup_routes(page)

        # ── [1] Indexing page ─────────────────────────────────────────────
        print("\n[1] Indexing page")
        page.goto(f"{FRONTEND}/indexing")
        page.wait_for_load_state("networkidle")
        _shot(page, "01_indexing")

        # Button is enabled only when hasActiveRepo (from mocked /connections/active)
        index_btn = page.locator("button", has_text="Indexar codigo").first
        expect(index_btn).to_be_enabled(timeout=8000)
        index_btn.click()

        # Wait for the success banner (shows duration after indexing)
        page.wait_for_selector("text=Indexacion completada", timeout=10000)
        _shot(page, "02_indexing_done")
        print("  [OK] Indexing successful")

        # ── [2] Workflow — Step 1: Understand Requirement ─────────────────
        print("\n[2] Workflow — Step 1")
        page.goto(f"{FRONTEND}/workflow")
        page.wait_for_load_state("networkidle")
        _shot(page, "03_step1_empty")

        # Fill requirement text
        textarea = page.locator("#requirement-text")
        expect(textarea).to_be_visible(timeout=8000)
        textarea.fill(REQ)
        _shot(page, "04_step1_filled")

        # Wait for button to become enabled (isReady requires: ticketConn + hasSite + hasRepo + isIndexed)
        analyze_btn = page.locator("button", has_text="Analizar requerimiento").first
        expect(analyze_btn).to_be_enabled(timeout=8000)
        analyze_btn.click()
        print("  [OK] Clicked 'Analizar requerimiento'")

        # ── [3] Workflow — Step 2: Impact Analysis ────────────────────────
        print("\n[3] Workflow — Step 2")
        impact_btn = page.locator("button", has_text="Analizar impacto").first
        expect(impact_btn).to_be_visible(timeout=8000)
        _shot(page, "05_step2")
        impact_btn.click()
        print("  [OK] Clicked 'Analizar impacto'")

        # ── [4] Workflow — Step 3: Generate Story ─────────────────────────
        # Step 3 auto-triggers story generation on mount; there is no
        # "Generar historia" button anymore. Wait for the generation to
        # finish (continue button appears) and click it.
        print("\n[4] Workflow — Step 3")
        continue_btn = page.locator("button", has_text="Continuar al ticket").first
        expect(continue_btn).to_be_visible(timeout=30000)
        _shot(page, "06_step3")
        continue_btn.click()
        print("  [OK] Story generated; clicked 'Continuar al ticket'")

        # ── [5] Workflow — Step 4: Create Ticket ──────────────────────────
        print("\n[5] Workflow — Step 4")
        # project-key is an <input> when jira-projects returns []
        project_key = page.locator("#project-key")
        expect(project_key).to_be_visible(timeout=8000)
        project_key.fill("SCRUM")
        _shot(page, "07_step4")

        create_btn = page.locator("button", has_text="Crear ticket").first
        expect(create_btn).to_be_enabled(timeout=5000)
        create_btn.click()
        print("  [OK] Clicked 'Crear ticket'")

        # ── [6] Assert success ────────────────────────────────────────────
        page.wait_for_selector("text=Ticket creado con exito", timeout=8000)
        _shot(page, "08_success")
        print("  [OK] Ticket creation confirmed")

        print(f"\n[DONE] E2E happy path complete — screenshots in {SCREENSHOTS_DIR}")

        page.close()
        ctx.close()
        browser.close()
