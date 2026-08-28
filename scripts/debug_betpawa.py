import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_default_timeout(15000)
    print("goto betpawa.cm")
    page.goto("https://www.betpawa.cm", wait_until="domcontentloaded")
    import time
    time.sleep(3)
    print("url", page.url)
    print("title", page.title())
    content = page.content()
    print(content[:5000])
    # try to find login elements
    for sel in ["text=Log in", "text=Login", "text=LOG IN", "button", "input"]:
        try:
            cnt = page.locator(sel).count()
            print(f"{sel!r} count {cnt}")
            if cnt>0 and cnt<10:
                for i in range(cnt):
                    try:
                        txt = page.locator(sel).nth(i).inner_text()[:100]
                        print(f"  [{i}] {txt!r}")
                    except: pass
        except Exception as e:
            print(f"err {sel} {e}")
    # screenshot
    page.screenshot(path="profiles/betpawa/debug.png")
    print("screenshot saved")
    browser.close()
