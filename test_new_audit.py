from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    # Desktop test
    context = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = context.new_page()
    page.goto('http://127.0.0.1:8080/audit/index.html', wait_until='networkidle')
    page.wait_for_timeout(1000)
    page.screenshot(path='audit-input-desktop.png', full_page=False)
    
    # Enable demo mode and run audit
    page.click('#demoMode')
    page.click('#analyzeBtn')
    page.wait_for_selector('#resultsSection.active', timeout=30000)
    page.wait_for_timeout(1000)
    page.screenshot(path='audit-result-desktop.png', full_page=False)
    
    # Test email action
    page.fill('#reportEmail', 'test@example.com')
    page.click('#sendReportBtn')
    page.wait_for_timeout(1500)
    page.screenshot(path='audit-action-desktop.png', full_page=False)
    
    # Mobile test
    context2 = browser.new_context(viewport={'width': 375, 'height': 812})
    page2 = context2.new_page()
    page2.goto('http://127.0.0.1:8080/audit/index.html', wait_until='networkidle')
    page2.wait_for_timeout(1000)
    page2.click('#demoMode')
    page2.click('#analyzeBtn')
    page2.wait_for_selector('#resultsSection.active', timeout=30000)
    page2.wait_for_timeout(1000)
    page2.screenshot(path='audit-result-mobile.png', full_page=False)
    
    browser.close()
    print('Audit page tests completed')
