from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = context.new_page()
    page.goto('http://127.0.0.1:8080/audit/index.html', wait_until='networkidle')
    page.wait_for_timeout(1000)
    
    # Ensure demo mode is NOT checked
    if page.is_checked('#demoMode'):
        page.click('#demoMode')
    
    page.fill('#siteUrl', 'http://127.0.0.1:9002')
    page.click('#analyzeBtn')
    page.wait_for_selector('#resultsSection.active', timeout=60000)
    page.wait_for_timeout(1000)
    page.screenshot(path='audit-api-mode.png', full_page=False)
    
    # Check if demo banner is hidden
    banner_visible = page.is_visible('#demoBanner.active')
    print('Demo banner visible:', banner_visible)
    
    browser.close()
    print('API mode test completed')
