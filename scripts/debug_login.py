from playwright.sync_api import sync_playwright
import time
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://www.betpawa.cm", wait_until="domcontentloaded")
    time.sleep(3)
    print("before click url", page.url)
    # click Login
    try:
        login_btn = page.locator("text=Login").first
        print("login btn count", page.locator("text=Login").count())
        print("login btn visible", login_btn.is_visible())
        login_btn.click()
        print("clicked Login")
        time.sleep(2)
        print("after click url", page.url)
        print("inputs after click", page.locator("input").count())
        for i in range(page.locator("input").count()):
            el = page.locator("input").nth(i)
            try:
                print(f"input {i}: placeholder={el.get_attribute('placeholder')!r} name={el.get_attribute('name')!r} type={el.get_attribute('type')!r} outer={el.evaluate('e=>e.outerHTML')[:300]}")
            except Exception as e:
                print(f"input {i} err {e}")
        # also check for password
        print("password count", page.locator("input[type='password']").count())
        page.screenshot(path="profiles/betpawa/debug2.png")
        print("screenshot2 saved")
    except Exception as e:
        print(f"err {e}")
        import traceback
        traceback.print_exc()
    browser.close()
