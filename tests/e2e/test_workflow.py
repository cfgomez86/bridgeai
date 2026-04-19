"""E2E test: full BridgeAI workflow via Chromium (Playwright).

REQUIREMENTS:
1. Frontend running: cd frontend && npm run dev
2. API running: python -m uvicorn app.main:app --reload
3. Playwright browser: npm install -D @playwright/test

RUN:
    pytest tests/e2e/ -v -s
"""
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:3000"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"

REQ = (
    "As a registered user I want to reset my password via email "
    "so that I can recover my account if I forget my credentials."
)


def shot(page, name: str) -> None:
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  [SCREENSHOT] {name}.png")


@pytest.mark.e2e
@pytest.mark.slow
def test_full_workflow():
    SCREENSHOTS_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # ── Check Frontend Available ──────────────────────────────────────
        print(f"\n[0] Checking frontend at {FRONTEND}…")
        try:
            page.goto(FRONTEND, timeout=10000)
            page.wait_for_load_state("networkidle", timeout=15000)
            print(f"  [OK] Frontend is available")
        except Exception as e:
            print(f"  [ERROR] Frontend not available at {FRONTEND}")
            print(f"     Make sure to run: cd frontend && npm run dev")
            print(f"     Error: {e}")
            raise

        # ── Indexing ──────────────────────────────────────────────────────
        print("\n[2] Indexing")
        page.goto(f"{FRONTEND}/indexing")
        page.wait_for_load_state("networkidle")
        shot(page, "02_indexing")

        idx_btn = page.get_by_role("button").filter(has_text="Index")
        if idx_btn.count():
            print("  clicking index button…")
            idx_btn.first.click()
            page.wait_for_timeout(6000)
            shot(page, "03_indexing_done")
        else:
            print("  index button not found, skipping")

        # ── Step 1: Understand Requirement ────────────────────────────────
        print("\n[3] Workflow — Step 1: Understand Requirement")
        page.goto(f"{FRONTEND}/workflow")
        page.wait_for_load_state("networkidle")
        shot(page, "04_step1_empty")

        page.locator("input#project-id").fill("browser-test")
        page.locator("textarea").fill(REQ)
        shot(page, "05_step1_filled")

        print("  waiting for Analyze Requirement button…")
        try:
            analyze_btn = page.get_by_role("button", name="Analyze Requirement")
            analyze_btn.wait_for(timeout=5000)
            print("  [OK] button found, clicking...")
            analyze_btn.click()
        except Exception as e:
            print(f"  [ERROR] {e}")
            shot(page, "ERROR_button_not_found")
            raise
        
        print("  waiting for Impact Analysis step (LLM ~30s)…")
        page.wait_for_selector("text=Impact Analysis", timeout=90000)
        shot(page, "06_step2_loaded")

        # ── Step 2: Impact Analysis ───────────────────────────────────────
        print("\n[4] Workflow — Step 2: Impact Analysis")
        try:
            impact_btn = page.get_by_role("button", name="Analyze Impact")
            impact_btn.wait_for(timeout=5000)
            print("  [OK] button found, clicking...")
            impact_btn.click()
        except Exception as e:
            print(f"  [ERROR] {e}")
            shot(page, "ERROR_impact_button_not_found")
            raise
        
        page.wait_for_selector("text=Impact Summary", timeout=30000)
        shot(page, "07_step2_done")

        # ── Step 3: Generate Story ────────────────────────────────────────
        print("\n[5] Workflow — Step 3: Generate Story")
        try:
            generate_btn = page.get_by_role("button", name="Generate Story")
            generate_btn.wait_for(timeout=5000)
            print("  [OK] button found, clicking...")
            print("  (LLM ~60-100s, waiting for response)...")
            with page.expect_response(
                lambda r: "/api/v1/generate-story" in r.url and r.request.method == "POST",
                timeout=180000,
            ) as resp_info:
                generate_btn.click()
            resp = resp_info.value
            print(f"  [OK] generate-story response: {resp.status}")
        except Exception as e:
            print(f"  [ERROR] {e}")
            shot(page, "ERROR_generate_button_not_found")
            raise
        
        page.wait_for_timeout(1500)
        shot(page, "08_step3_done")

        # ── Step 4: Create Ticket ─────────────────────────────────────────
        print("\n[6] Workflow — Step 4: Create Ticket")
        shot(page, "09_step4_loaded")

        project_key_input = page.locator(
            "input[placeholder*='project' i], input[placeholder*='key' i]"
        )
        if project_key_input.count():
            project_key_input.first.fill("BRIDGE")
            shot(page, "10_step4_filled")

        print("  [WARN] (skipping ticket creation - requires valid Jira project)")

        page.wait_for_timeout(1000)
        shot(page, "11_final")

        print(f"\n[DONE] ALL COMPLETE - screenshots in {SCREENSHOTS_DIR}")
        page.wait_for_timeout(2000)
        
        print("\nClosing browser...")
        page.close()
        ctx.close()
        browser.close()
        print("[OK] Browser closed")


if __name__ == "__main__":
    test_full_workflow()
