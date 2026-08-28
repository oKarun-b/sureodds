from playwright.sync_api import sync_playwright
import time
import os
from dotenv import load_dotenv
load_dotenv("C:/Users/PC/sureodds/.env")
user = os.getenv("BETPAWA_USER")
pwd = os.getenv("BETPAWA_PASS")
print(f"user {user}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    page = browser.new_page()
    # listen to responses
    def handle_response(resp):
        if "login" in resp.url or "auth" in resp.url or "api" in resp.url:
            print(f"resp {resp.url} {resp.status}")
            try:
                print(resp.text()[:500])
            except: pass
    page.on("response", handle_response)
    page.goto("https://www.betpawa.cm", wait_until="domcontentloaded")
    time.sleep(2)
    page.locator("text=Login").first.click()
    time.sleep(1)
    page.locator("input[name='username']").fill(user)
    time.sleep(0.5)
    page.locator("input[name='password']").fill(pwd)
    time.sleep(0.5)
    page.locator("[data-test-id='login-form-submit-button'], button:has-text('Login')").first.click()
    time.sleep(4)
    print("url", page.url)
    # check error list
    for sel in [".LoginForm_errorList", "[data-test-id='login-form-error']", "ul", "[role='alert']"]:
        try:
            cnt = page.locator(sel).count()
            print(f"{sel} count {cnt}")
            for i in range(min(cnt,3)):
                try:
                    txt = page.locator(sel).nth(i).inner_text()[:500]
                    print(f"  [{i}] {txt!r}")
                    html = page.locator(sel).nth(i).evaluate("e=>e.outerHTML")[:1000]
                    print(f"  html {html[:500]!r}")
                except Exception as e:
                    print(f"  err {e}")
        except: pass
    # full body text
    try:
        body = page.locator("body").inner_text()[:2000]
        print("body text:", body[:1000])
    except: pass
    page.screenshot(path="profiles/betpawa/debug_login3.png", full_page=True)
    print("screenshot3 saved")
    browser.close()
