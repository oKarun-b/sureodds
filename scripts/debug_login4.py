from playwright.sync_api import sync_playwright
import time, os
from dotenv import load_dotenv
load_dotenv("C:/Users/PC/sureodds/.env")
user=os.getenv("BETPAWA_USER")
pwd=os.getenv("BETPAWA_PASS")
print(f"user {user} pwd {pwd}")

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    page=browser.new_page()
    responses=[]
    def handle_response(resp):
        if "login" in resp.url.lower() or "auth" in resp.url.lower() or "api" in resp.url.lower():
            print(f"resp {resp.url} {resp.status}")
            try:
                txt=resp.text()[:1000]
                print(f"  body {txt[:500]!r}")
            except: pass
            responses.append(resp.url)
    page.on("response", handle_response)
    page.goto("https://www.betpawa.cm", wait_until="domcontentloaded")
    time.sleep(2)
    print("click Login")
    page.locator("text=Login").first.click()
    time.sleep(1)
    print("fill phone")
    page.locator("input[name='username']").fill(user)
    time.sleep(0.5)
    print("fill pwd")
    page.locator("input[name='password']").fill(pwd)
    time.sleep(0.5)
    # check button
    btn=page.locator("[data-test-id='log-in-button']")
    print(f"btn count {btn.count()} enabled {btn.first.is_enabled()} visible {btn.first.is_visible()}")
    print(f"btn text {btn.first.inner_text()[:50]!r}")
    btn.first.click()
    print("clicked LOG IN")
    time.sleep(5)
    print("url", page.url)
    # check for logout/balance
    for sel in ["text=Log out", "text=Logout", "text=Balance", "text=My Bets", "text=Deposit"]:
        print(f"{sel} count {page.locator(sel).count()}")
    # check error
    for sel in [".LoginForm_errorList", "[data-test-id='login-form-error']", "text=Invalid", "text=incorrect", "text=Error"]:
        try:
            cnt=page.locator(sel).count()
            if cnt>0:
                print(f"{sel} found {cnt}: {page.locator(sel).first.inner_text()[:500]!r}")
        except: pass
    # dump body
    try:
        body=page.locator("body").inner_text()[:2000]
        print("body:", body[:1000])
    except: pass
    page.screenshot(path="profiles/betpawa/debug_login4.png", full_page=True)
    print("screenshot saved")
    browser.close()
