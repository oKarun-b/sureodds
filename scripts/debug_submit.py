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
    page.locator("text=Login").first.click()
    time.sleep(1)
    # check form
    print("phone input count", page.locator("input[name='username']").count())
    print("phone html", page.locator("input[name='username']").evaluate("e=>e.outerHTML")[:500])
    print("pwd html", page.locator("input[name='password']").evaluate("e=>e.outerHTML")[:500])
    # fill
    page.locator("input[name='username']").fill(user)
    time.sleep(0.5)
    page.locator("input[name='password']").fill(pwd)
    time.sleep(0.5)
    # check submit button
    for sel in ["[data-test-id='login-form-submit-button']", "button:has-text('Login')", "button[type='submit']"]:
        cnt=page.locator(sel).count()
        print(f"{sel} count {cnt}")
        for i in range(min(cnt,3)):
            try:
                el=page.locator(sel).nth(i)
                print(f"  [{i}] text={el.inner_text()[:30]!r} enabled={el.is_enabled()} visible={el.is_visible()} html={el.evaluate('e=>e.outerHTML')[:400]!r}")
            except Exception as e:
                print(f"  err {e}")
    # check if button disabled
    btn=page.locator("[data-test-id='login-form-submit-button']").first
    print("submit enabled", btn.is_enabled())
    print("submit visible", btn.is_visible())
    # try to click
    try:
        btn.click()
        print("clicked submit")
    except Exception as e:
        print(f"click err {e}")
    time.sleep(4)
    print("url", page.url)
    # check for error
    for sel in [".LoginForm_errorList", "[data-test-id='login-form-error']"]:
        try:
            print(f"{sel} count {page.locator(sel).count()}")
            if page.locator(sel).count()>0:
                print(page.locator(sel).first.inner_text()[:500])
        except: pass
    # check for logout
    for sel in ["text=Log out", "text=Logout", "text=Balance"]:
        print(f"{sel} count {page.locator(sel).count()}")
    page.screenshot(path="profiles/betpawa/debug_submit.png", full_page=True)
    print("screenshot saved")
    browser.close()
