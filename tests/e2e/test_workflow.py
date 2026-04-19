"""E2E test: full BridgeAI workflow via Chromium (Playwright)."""
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
    print(f"  screenshot: {name}.png")


def test_full_workflow():
    SCREENSHOTS_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # ── Home ──────────────────────────────────────────────────────────
        print("\n[1] Home")
        page.goto(FRONTEND)
        page.wait_for_load_state("networkidle")
        shot(page, "01_home")
        print(f"  title: {page.title()}")

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

        print("  clicking Analyze Requirement (LLM ~30s)…")
        page.get_by_role("button", name="Analyze Requirement").click()
        page.wait_for_selector("text=Impact Analysis", timeout=90000)
        shot(page, "06_step2_loaded")

        # ── Step 2: Impact Analysis ───────────────────────────────────────
        print("\n[4] Workflow — Step 2: Impact Analysis")
        page.get_by_role("button", name="Analyze Impact").click()
        page.wait_for_selector("text=Impact Summary", timeout=30000)
        shot(page, "07_step2_done")

        # ── Step 3: Generate Story ────────────────────────────────────────
        print("\n[5] Workflow — Step 3: Generate Story")
        print("  clicking Generate Story (LLM ~60-100s)…")
        with page.expect_response(
            lambda r: "/api/v1/generate-story" in r.url and r.request.method == "POST",
            timeout=180000,
        ) as resp_info:
            page.get_by_role("button", name="Generate Story").click()
        resp = resp_info.value
        print(f"  generate-story response: {resp.status}")
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

        print("  (skipping ticket creation — requires valid Jira project)")

        page.wait_for_timeout(1000)
        shot(page, "11_final")

        print(f"\n=== ALL DONE — screenshots in {SCREENSHOTS_DIR} ===")
        page.wait_for_timeout(3000)
        browser.close()


if __name__ == "__main__":
    test_full_workflow()
