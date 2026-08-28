from playwright.sync_api import sync_playwright
import time, os
from dotenv import load_dotenv
load_dotenv("C:/Users/PC/sureodds/.env")
user=os.getenv("BETPAWA_USER")
pwd=os.getenv("BETPAWA_PASS")
print(f"user {user}")

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    page=browser.new_page()
    page.goto("https://www.betpawa.cm", wait_until="domcontentloaded")
    time.sleep(2)
    # click Login
    if page.locator("text=Login").count()>0:
        page.locator("text=Login").first.click()
        time.sleep(1)
        try:
            page.wait_for_url("**/login", timeout=5000)
            print("navigated to login")
        except: print("no nav")
    # fill
    phone_sel="input[name='username'], #phoneNumber, [data-test-id='login-form-phone-number-input']"
    for _ in range(20):
        if page.locator(phone_sel).count()>0:
            break
        time.sleep(0.5)
    print("phone found", page.locator(phone_sel).count())
    page.locator(phone_sel).first.fill(user)
    time.sleep(0.5)
    page.locator("input[name='password']").fill(pwd)
    time.sleep(0.5)
    submit_sel="[data-test-id='log-in-button'], button:has-text('LOG IN')"
    print("submit count", page.locator(submit_sel).count())
    print("submit enabled", page.locator(submit_sel).first.is_enabled())
    page.locator(submit_sel).first.click()
    print("clicked")
    time.sleep(5)
    print("url", page.url)
    # check for balance
    for sel in ["text=Balance", "text=My Bets", "text=Log out", ".LoginForm_errorList", "[data-test-id='login-form-error']"]:
        try:
            cnt=page.locator(sel).count()
            print(f"{sel} count {cnt}")
            if cnt>0:
                print(page.locator(sel).first.inner_text()[:500])
        except: pass
    # check for error list
    try:
        body=page.locator("body").inner_text()[:3000]
        print("body:", body[:1000])
    except: pass
    # network: check last responses
    page.screenshot(path="profiles/betpawa/debug_final.png", full_page=True)
    print("screenshot saved")
    browser.close()
