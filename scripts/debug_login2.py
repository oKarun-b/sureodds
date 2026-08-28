from playwright.sync_api import sync_playwright
import time, re
from pathlib import Path

# use credentials from .env
import os
from dotenv import load_dotenv
load_dotenv("C:/Users/PC/sureodds/.env")
user = os.getenv("BETPAWA_USER")
pwd = os.getenv("BETPAWA_PASS")
print(f"user {user} pwd len {len(pwd) if pwd else 0}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    page = browser.new_page()
    page.set_default_timeout(15000)
    page.goto("https://www.betpawa.cm", wait_until="domcontentloaded")
    time.sleep(2)
    print("before login url", page.url)
    # click Login
    try:
        login_btn = page.locator("text=Login").first
        print("login btn visible", login_btn.is_visible())
        login_btn.click()
        print("clicked Login")
        time.sleep(2)
    except Exception as e:
        print(f"click err {e}")
    # fill
    try:
        phone_sel = "input[name='username'], #phoneNumber, [data-test-id='login-form-phone-number-input']"
        page.wait_for_selector(phone_sel, timeout=8000)
        print("phone visible")
        page.locator(phone_sel).first.fill(user)
        print("filled phone")
        time.sleep(0.5)
        page.locator("input[name='password'], [data-test-id='login-form-password-input']").first.fill(pwd)
        print("filled pwd")
        time.sleep(0.5)
        # find submit
        submit_sel = "[data-test-id='login-form-submit-button'], button:has-text('Login')"
        print("submit count", page.locator(submit_sel).count())
        for i in range(page.locator(submit_sel).count()):
            try:
                txt = page.locator(submit_sel).nth(i).inner_text()[:50]
                print(f"submit {i}: {txt!r} visible {page.locator(submit_sel).nth(i).is_visible()}")
            except: pass
        page.locator(submit_sel).first.click()
        print("clicked submit")
        time.sleep(4)
        print("after submit url", page.url)
        content = page.content()
        print(content[content.find("Log"):content.find("Log")+2000][:2000])
        # check for error messages
        for sel in ["text=Invalid", "text=incorrect", "text=Error", "text=failed", "[role='alert']"]:
            try:
                cnt = page.locator(sel).count()
                if cnt>0:
                    print(f"{sel} found {cnt}: {page.locator(sel).first.inner_text()[:200]!r}")
            except: pass
        # check for logout/balance
        for sel in ["text=Log out", "text=Logout", "text=Déconnexion", "text=Balance", "text=My Bets"]:
            try:
                cnt = page.locator(sel).count()
                print(f"{sel} count {cnt}")
                if cnt>0:
                    print(f"  text: {page.locator(sel).first.inner_text()[:100]!r}")
            except: pass
        page.screenshot(path="profiles/betpawa/debug_login.png", full_page=True)
        print("screenshot saved")
    except Exception as e:
        print(f"err {e}")
        import traceback
        traceback.print_exc()
        page.screenshot(path="profiles/betpawa/debug_login_err.png", full_page=True)
    browser.close()
