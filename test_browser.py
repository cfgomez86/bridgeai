"""Browser E2E test: runs the full BridgeAI workflow via Chromium."""
import os
from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:3000"
SHOTS = "/c/proyectos/bridgeai/screenshots"
os.makedirs(SHOTS, exist_ok=True)

REQ = (
    "As a registered user I want to reset my password via email "
    "so that I can recover my account if I forget my credentials."
)

def shot(page, name):
    path = f"{SHOTS}/{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"  screenshot: {name}.png")

def run():
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

        # ── Workflow Step 1: Understand ───────────────────────────────────
        print("\n[3] Workflow — Step 1: Understand Requirement")
        page.goto(f"{FRONTEND}/workflow")
        page.wait_for_load_state("networkidle")
        shot(page, "04_step1_empty")

        # Fill project ID
        proj_input = page.locator("input#project-id")
        proj_input.fill("browser-test")

        # Fill requirement
        page.locator("textarea").fill(REQ)
        shot(page, "05_step1_filled")

        # Click "Analyze Requirement"
        print("  clicking Analyze Requirement (LLM ~30s)…")
        page.get_by_role("button", name="Analyze Requirement").click()
        # Step 2 loads when the "Impact Analysis" card header appears
        page.wait_for_selector("text=Impact Analysis", timeout=90000)
        shot(page, "06_step2_loaded")

        # ── Workflow Step 2: Impact Analysis ─────────────────────────────
        print("\n[4] Workflow — Step 2: Impact Analysis")
        print("  clicking Analyze Impact (fast)…")
        page.get_by_role("button", name="Analyze Impact").click()
        # Step 3 loads when "Generate Story" button or "Impact Summary" card appears
        page.wait_for_selector("text=Impact Summary", timeout=30000)
        shot(page, "07_step2_done")

        # ── Workflow Step 3: Generate Story ───────────────────────────────
        print("\n[5] Workflow — Step 3: Generate Story")
        print("  clicking Generate Story (LLM ~60-100s)…")
        # Wait for the /generate-story API response BEFORE clicking so we can intercept it
        with page.expect_response(
            lambda r: "/api/v1/generate-story" in r.url and r.request.method == "POST",
            timeout=180000
        ) as resp_info:
            page.get_by_role("button", name="Generate Story").click()
        resp = resp_info.value
        print(f"  generate-story response: {resp.status}")
        # Give React time to fully render Step 4 after state update
        page.wait_for_timeout(1500)
        shot(page, "08_step3_done")

        # ── Workflow Step 4: Create Ticket ────────────────────────────────
        print("\n[6] Workflow — Step 4: Create Ticket")
        shot(page, "09_step4_loaded")

        # Fill ticket form fields if visible
        project_key_input = page.locator("input[placeholder*='project' i], input[placeholder*='key' i]")
        if project_key_input.count():
            project_key_input.first.fill("BRIDGE")
            shot(page, "10_step4_filled")

        print("  (skipping actual ticket creation — requires valid Jira project)")

        # Final screenshot
        page.wait_for_timeout(1000)
        shot(page, "11_final")

        print(f"\n=== ALL DONE — screenshots in {SHOTS} ===")
        page.wait_for_timeout(3000)
        browser.close()

if __name__ == "__main__":
    run()
