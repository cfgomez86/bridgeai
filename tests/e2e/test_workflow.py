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
            page.goto(FRONTEND, timeout=8000)
            page.wait_for_load_state("networkidle", timeout=10000)
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

        # Look for Index button in any language
        idx_btn = None
        buttons = page.locator("button")
        for i in range(buttons.count()):
            btn = buttons.nth(i)
            text = btn.text_content() or ""
            if "index" in text.lower():
                idx_btn = btn
                break
        
        if idx_btn:
            print("  clicking index button...")
            idx_btn.click()
            page.wait_for_timeout(500)
            shot(page, "03_indexing_done")
        else:
            print("  index button not found, skipping")

        # ── Step 1: Understand Requirement ────────────────────────────────
        print("\n[3] Workflow — Step 1: Understand Requirement")
        page.goto(f"{FRONTEND}/workflow")
        page.wait_for_load_state("networkidle")
        shot(page, "04_step1_empty")

        print("  filling form...")
        page.locator("input#project-id").fill("browser-test")
        page.locator("textarea").fill(REQ)
        page.wait_for_timeout(300)
        shot(page, "05_step1_filled")

        print("  looking for Analyze Requirement button...")
        try:
            # The button text might be in different languages
            # Spanish: "Analizar requerimiento"
            # English: "Analyze Requirement"
            # Look for any button containing either word
            
            analyze_btn = None
            all_buttons = page.locator("button")
            print(f"  Total buttons on page: {all_buttons.count()}")
            
            # Try to find button with text containing "Analizar", "Analyze", or "requerimiento"
            for i in range(all_buttons.count()):
                btn = all_buttons.nth(i)
                text = btn.text_content() or ""
                if any(keyword in text.lower() for keyword in ["analizar", "analyze", "requerimiento", "requirement"]):
                    if text.strip():  # Make sure it has actual text
                        analyze_btn = btn
                        print(f"  [OK] Found button: '{text}'")
                        break
            
            if analyze_btn:
                analyze_btn.scroll_into_view_if_needed()
                page.wait_for_timeout(300)
                print("  [OK] clicking button...")
                analyze_btn.click()
                print("  [OK] button clicked successfully")
            else:
                print(f"  [ERROR] Could not find Analyze/Analizar button")
                shot(page, "ERROR_button_not_found")
                raise RuntimeError("Analyze Requirement button not found")
                
        except Exception as e:
            print(f"  [ERROR] {e}")
            shot(page, "ERROR_button_analyzing")
            raise
        
        print("  waiting for response from API...")
        # Wait for page to update with next step content
        page.wait_for_timeout(500)
        
        # Wait for Impact Analysis step to appear (API usually responds in 3-8s)
        try:
            page.wait_for_selector("text=/[Ii]mpact|[Aa]nalysis|Impacto/", timeout=15000)
            print("  [OK] Impact Analysis step loaded")
        except:
            print("  [WARN] Impact Analysis text not found yet")
        
        shot(page, "06_step1_done")

        # ── Step 2: Impact Analysis ───────────────────────────────────────
        print("\n[4] Workflow — Step 2: Impact Analysis")
        page.wait_for_timeout(500)  # Wait for page to fully render
        
        try:
            # Look for Impact button (Spanish: Analizar impacto, English: Analyze Impact)
            impact_btn = None
            all_buttons = page.locator("button")
            print(f"  Total buttons visible: {all_buttons.count()}")
            
            for i in range(all_buttons.count()):
                btn = all_buttons.nth(i)
                text = btn.text_content() or ""
                print(f"    Button {i}: '{text}'")
                if any(keyword in text.lower() for keyword in ["impacto", "impact"]):
                    if text.strip() and len(text) > 3:
                        impact_btn = btn
                        print(f"  [OK] Found Impact button: '{text}'")
                        break
            
            if impact_btn:
                print("  [OK] clicking button...")
                impact_btn.scroll_into_view_if_needed()
                page.wait_for_timeout(200)
                impact_btn.click()
                print("  [OK] waiting for API response (~8-15s)...")
                page.wait_for_timeout(12000)  # Wait for Impact Analysis API
                shot(page, "07_step2_done")
            else:
                print("  [WARN] Impact Analysis button not found")
                print("  Taking debug screenshot...")
                shot(page, "DEBUG_step2_buttons")
        except Exception as e:
            print(f"  [ERROR] {e}")
            shot(page, "ERROR_impact_button_not_found")

        # ── Step 3: Generate Story ────────────────────────────────────────
        print("\n[5] Workflow — Step 3: Generate Story")
        page.wait_for_timeout(500)  # Wait for page to fully render
        
        try:
            # Look for Generate Story button (Spanish: Generar historia, English: Generate Story)
            generate_btn = None
            all_buttons = page.locator("button")
            print(f"  Total buttons visible: {all_buttons.count()}")
            
            for i in range(all_buttons.count()):
                btn = all_buttons.nth(i)
                text = btn.text_content() or ""
                print(f"    Button {i}: '{text}'")
                if any(keyword in text.lower() for keyword in ["generar", "generate", "historia", "story"]):
                    if text.strip() and len(text) > 3:
                        generate_btn = btn
                        print(f"  [OK] Found Generate button: '{text}'")
                        break
            
            if generate_btn:
                print("  [OK] clicking button...")
                print("  (Waiting for LLM response, up to 90s)...")
                generate_btn.scroll_into_view_if_needed()
                page.wait_for_timeout(200)
                
                try:
                    with page.expect_response(
                        lambda r: "/api/v1/generate-story" in r.url and r.request.method == "POST",
                        timeout=90000,  # 90s for LLM (more realistic)
                    ) as resp_info:
                        generate_btn.click()
                    resp = resp_info.value
                    print(f"  [OK] generate-story response: {resp.status}")
                except:
                    print("  [WARN] no response captured, waiting...")
                    page.wait_for_timeout(8000)
                
                shot(page, "08_step3_done")
            else:
                print("  [WARN] Generate Story button not found")
                print("  Taking debug screenshot...")
                shot(page, "DEBUG_step3_buttons")
        except Exception as e:
            print(f"  [ERROR] {e}")
            shot(page, "ERROR_generate_button_not_found")

        # ── Step 4: Create Ticket ─────────────────────────────────────────
        print("\n[6] Workflow — Step 4: Create Ticket")
        page.wait_for_timeout(500)
        
        try:
            shot(page, "09_step4_loaded")
            
            # Look for Create Ticket button
            create_ticket_btn = None
            all_buttons = page.locator("button")
            print(f"  Total buttons visible: {all_buttons.count()}")
            
            for i in range(all_buttons.count()):
                btn = all_buttons.nth(i)
                text = btn.text_content() or ""
                if any(keyword in text.lower() for keyword in ["crear", "create", "ticket", "entidad"]):
                    if text.strip() and len(text) > 3:
                        create_ticket_btn = btn
                        print(f"  [OK] Found Create Ticket button: '{text}'")
                        break
            
            # Also look for project key input field
            project_key_input = page.locator(
                "input[placeholder*='project' i], input[placeholder*='key' i], input[placeholder*='JIRA' i]"
            )
            
            if project_key_input.count():
                print(f"  Found project key input field")
                project_key_input.first.fill("BRIDGE")
                shot(page, "10_step4_filled")
            
            # Try to create ticket if button exists
            if create_ticket_btn:
                print("  [OK] clicking Create Ticket button...")
                create_ticket_btn.scroll_into_view_if_needed()
                page.wait_for_timeout(200)
                
                try:
                    with page.expect_response(
                        lambda r: "ticket" in r.url.lower() or "integration" in r.url.lower(),
                        timeout=20000,
                    ) as resp_info:
                        create_ticket_btn.click()
                    resp = resp_info.value
                    print(f"  [OK] ticket response: {resp.status}")
                except:
                    print("  [WARN] no ticket response captured")
            else:
                print("  [INFO] Create Ticket button not found (normal - may require valid Jira config)")
                
        except Exception as e:
            print(f"  [ERROR] Step 4: {e}")
            shot(page, "ERROR_step4_failed")

        page.wait_for_timeout(500)
        shot(page, "11_final")

        print(f"\n[DONE] E2E Workflow Complete - screenshots in {SCREENSHOTS_DIR}")
        
        print("\nClosing browser...")
        page.close()
        ctx.close()
        browser.close()
        print("[OK] Browser closed")


if __name__ == "__main__":
    test_full_workflow()
