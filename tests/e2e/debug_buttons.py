"""Debug script to inspect button text on the workflow page."""
from playwright.sync_api import sync_playwright
import json

FRONTEND = "http://localhost:3000"
REQ = (
    "As a registered user I want to reset my password via email "
    "so that I can recover my account if I forget my credentials."
)

def print_buttons(page, step_name):
    """Helper to print all buttons on page."""
    print(f"\n=== {step_name} ===")
    buttons = page.locator("button")
    print(f"Total buttons: {buttons.count()}\n")
    
    for i in range(buttons.count()):
        btn = buttons.nth(i)
        text = btn.text_content() or ""
        visible = btn.is_visible()
        print(f"Button {i}: '{text}' (visible: {visible})")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=200)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()

    # Navigate to workflow
    print("Loading workflow page...")
    page.goto(f"{FRONTEND}/workflow")
    page.wait_for_load_state("networkidle")
    
    # Fill form
    print("Filling form...")
    page.locator("input#project-id").fill("test")
    page.locator("textarea").fill(REQ)
    page.wait_for_timeout(1000)
    
    print_buttons(page, "STEP 1 - After filling form")
    
    # Click analyze button
    analyze_btn = None
    all_buttons = page.locator("button")
    for i in range(all_buttons.count()):
        btn = all_buttons.nth(i)
        text = btn.text_content() or ""
        if any(kw in text.lower() for kw in ["analizar", "analyze", "requerimiento", "requirement"]):
            if text.strip():
                analyze_btn = btn
                print(f"\nFound Analyze button: '{text}'")
                break
    
    if analyze_btn:
        print("Clicking analyze button...")
        analyze_btn.click()
        print("Waiting 5 seconds for API response...")
        page.wait_for_timeout(5000)
        
        print_buttons(page, "STEP 2 - After clicking Analyze (5s wait)")
        
        print("\nWaiting 10 more seconds...")
        page.wait_for_timeout(10000)
        
        print_buttons(page, "STEP 2 - After clicking Analyze (15s total wait)")
        
        # Try to find Impact button
        impact_btn = None
        all_buttons = page.locator("button")
        for i in range(all_buttons.count()):
            btn = all_buttons.nth(i)
            text = btn.text_content() or ""
            if any(kw in text.lower() for kw in ["impacto", "impact"]):
                if text.strip():
                    impact_btn = btn
                    print(f"\nFound Impact button: '{text}'")
                    break
        
        if impact_btn:
            print("Clicking impact button...")
            impact_btn.click()
            print("Waiting 10 seconds for API response...")
            page.wait_for_timeout(10000)
            
            print_buttons(page, "STEP 3 - After clicking Impact")
    
    print("\n" + "="*50)
    print("Full page HTML (first 2000 chars):")
    print("="*50)
    html = page.content()
    print(html[:2000])
    
    input("\nPress Enter to close browser...")
    page.close()
    ctx.close()
    browser.close()
