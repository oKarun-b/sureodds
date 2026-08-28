from __future__ import annotations

import random
import re
import time
from pathlib import Path
from urllib.parse import quote_plus

from ..core.models import Slip
from .base import Receipt

DEFAULT_PROFILE = Path("profiles/betpawa")
DEFAULT_URL = "https://www.betpawa.cm"


def _human_delay(a: float = 0.3, b: float = 1.1) -> None:
    time.sleep(random.uniform(a, b))


def _random_viewport() -> dict:
    return {
        "width": random.randint(1280, 1440),
        "height": random.randint(800, 900),
    }


class BetpawaPlaywright:
    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        profile_dir: str | Path = DEFAULT_PROFILE,
        base_url: str = DEFAULT_URL,
        headless: bool = True,
        timeout_ms: int = 30000,
    ) -> None:
        self.username = username
        self.password = password
        self.profile_dir = Path(profile_dir)
        self.base_url = base_url.rstrip("/")
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    @property
    def storage_path(self) -> Path:
        return self.profile_dir / "storage_state.json"

    def _require_playwright(self):
        try:
            from playwright.sync_api import sync_playwright  # type: ignore

            return sync_playwright
        except ImportError as e:
            raise RuntimeError(
                "playwright not installed. Run: python -m uv sync --group integration && python -m uv run playwright install chromium"
            ) from e

    def login_and_save_session(self) -> Path:
        sync_playwright = self._require_playwright()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless, args=["--disable-blink-features=AutomationControlled"])
            context = browser.new_context(viewport=_random_viewport())
            page = context.new_page()
            page.set_default_timeout(self.timeout_ms)
            page.goto(self.base_url, wait_until="domcontentloaded")
            _human_delay(1.0, 1.5)
            # try auto-fill if credentials provided
            if self.username and self.password:
                try:
                    # open login modal if needed
                    if page.locator("text=Login").count() > 0 and not self._ensure_logged_in(page):
                        page.locator("text=Login").first.click()
                        _human_delay(1.0, 1.5)
                        # wait for navigation to /login
                        try:
                            page.wait_for_url("**/login", timeout=5000)
                        except Exception:
                            pass
                        _human_delay(0.5, 0.9)
                    phone_sel = "input[name='username'], #phoneNumber, [data-test-id='login-form-phone-number-input']"
                    # poll for phone input (BetPawa loads JS, may take a few seconds)
                    for _ in range(20):
                        if page.locator(phone_sel).count() > 0 and page.locator(phone_sel).first.is_visible():
                            break
                        page.wait_for_timeout(500)
                    else:
                        raise RuntimeError(f"phone input not found: {phone_sel}")
                    page.locator(phone_sel).first.fill(self.username)
                    _human_delay(0.2, 0.5)
                    page.locator("input[name='password'], [data-test-id='login-form-password-input']").first.fill(self.password)
                    _human_delay(0.2, 0.5)
                    # BetPawa Cameroon uses data-test-id log-in-button with text LOG IN
                    submit_sel = "[data-test-id='log-in-button'], button:has-text('LOG IN')"
                    page.locator(submit_sel).first.click()
                    # poll for logged-in state (Balance/My Bets appear, Log out may be hidden in menu)
                    for _ in range(30):
                        if page.locator("text=Balance").count() > 0 or page.locator("text=My Bets").count() > 0:
                            break
                        page.wait_for_timeout(500)
                    else:
                        # fallback: check URL or storage
                        page.wait_for_timeout(2000)
                    if not (page.locator("text=Balance").count() > 0 or page.locator("text=My Bets").count() > 0):
                        raise RuntimeError("login did not show Balance/My Bets")
                    print("Auto-login succeeded")
                except Exception as e:
                    print(f"Auto-login failed: {e}")
                    if not self.headless:
                        print(f"Opening {self.base_url} — log in manually, then press Enter...")
                        try:
                            page.wait_for_selector("text=Log out", timeout=300000)
                        except Exception:
                            input("Press Enter after you have logged in and see your balance...")
                    else:
                        raise RuntimeError(f"headless auto-login failed: {e}") from e
            else:
                print(f"Opening {self.base_url} — log in manually, then press Enter in this terminal...")
                try:
                    page.wait_for_selector("text=Log out", timeout=300000)
                except Exception:
                    input("Press Enter after you have logged in and see your balance...")
            context.storage_state(path=str(self.storage_path))
            print(f"Session saved to {self.storage_path}")
            browser.close()
        return self.storage_path

    def _new_page(self, p):
        storage = str(self.storage_path) if self.storage_path.exists() else None
        browser = p.chromium.launch(headless=self.headless, args=["--disable-blink-features=AutomationControlled"])
        context_kwargs: dict = {"viewport": _random_viewport()}
        if storage:
            context_kwargs["storage_state"] = storage
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.set_default_timeout(self.timeout_ms)
        return browser, context, page

    def _ensure_logged_in(self, page) -> bool:
        # check for balance or username indicator
        try:
            # balance is usually shown after login
            if page.locator("text=Log out").count() > 0:
                return True
            if page.locator("text=Balance").count() > 0:
                return True
        except Exception:
            pass
        return False

    def _clear_betslip(self, page) -> None:
        try:
            # common: "Clear" or trash icon in betslip
            for sel in ["text=Clear", "text=Remove all", "[aria-label*='Clear']"]:
                loc = page.locator(sel)
                if loc.count() > 0 and loc.first.is_visible():
                    loc.first.click()
                    _human_delay(0.3, 0.6)
                    break
        except Exception:
            pass

    def place(self, slip: Slip, dry_run: bool = False) -> Receipt:
        sync_playwright = self._require_playwright()
        with sync_playwright() as p:
            browser, context, page = self._new_page(p)
            try:
                page.goto(self.base_url, wait_until="domcontentloaded")
                _human_delay(1.5, 2.0)
                # wait a moment for either Balance (logged in via storage) or Login button to appear
                for _ in range(8):
                    if self._ensure_logged_in(page) or page.locator("text=Login").first.is_visible():
                        break
                    page.wait_for_timeout(500)

                if not self._ensure_logged_in(page) and self.username and self.password:
                    # try auto login - only if Login button is actually visible (not logged in via storage)
                    try:
                        login_btn = page.locator("text=Login").first
                        if login_btn.count() == 0 or not login_btn.is_visible():
                            # maybe already on login page, check for phone input directly
                            pass
                        else:
                            login_btn.click()
                            _human_delay(0.5, 0.9)
                        phone_sel = "input[name='username'], #phoneNumber, [data-test-id='login-form-phone-number-input']"
                        page.locator(phone_sel).first.fill(self.username)
                        _human_delay(0.2, 0.5)
                        page.locator("input[name='password'], [data-test-id='login-form-password-input']").first.fill(self.password)
                        _human_delay(0.2, 0.5)
                        page.locator("[data-test-id='log-in-button'], button:has-text('LOG IN')").first.click()
                        page.wait_for_timeout(3000)
                    except Exception as e:
                        return Receipt(False, error=f"auto-login failed: {e}")

                if not self._ensure_logged_in(page):
                    # still not logged in — cannot place
                    page.screenshot(path=str(self.profile_dir / f"place_{slip.date}_not_logged.png"))
                    return Receipt(False, error="not logged in — run `sureodds betpawa-login` first")

                self._clear_betslip(page)

                # add each leg
                for leg in slip.legs:
                    # navigate to search or directly to event
                    # BetPawa search is /search?query= ; fallback is to use homepage search input
                    query = quote_plus(f"{leg.fixture.home} {leg.fixture.away}")
                    # try direct search URL
                    page.goto(f"{self.base_url}/search?query={query}", wait_until="domcontentloaded")
                    _human_delay(0.6, 1.0)

                    # if 2UP eligible, ensure we are on 1X2 2UP market
                    if leg.eligible_2up:
                        try:
                            # toggle or tab labelled "1X2 2UP"
                            toggle = page.locator("text=1X2 2UP")
                            if toggle.count() > 0:
                                toggle.first.click()
                                _human_delay(0.4, 0.8)
                        except Exception:
                            pass

                    # find odds button for this leg
                    # side mapping: HOME -> first odds, DRAW -> second, AWAY -> third, but we match by odds value
                    odds_str = f"{leg.odds:.2f}".rstrip("0").rstrip(".")
                    # also try formatted with 2 decimals
                    candidates = [f"{leg.odds:.2f}", odds_str]
                    clicked = False
                    for cand in candidates:
                        # look for button containing odds text near team names
                        loc = page.locator(f"button:has-text('{cand}'), [role='button']:has-text('{cand}')")
                        # filter by visibility and count
                        n = loc.count()
                        for idx in range(min(n, 5)):
                            try:
                                el = loc.nth(idx)
                                if el.is_visible():
                                    # humanized move + click
                                    el.scroll_into_view_if_needed()
                                    _human_delay(0.2, 0.5)
                                    el.click()
                                    clicked = True
                                    break
                            except Exception:
                                continue
                        if clicked:
                            break
                    if not clicked:
                        page.screenshot(path=str(self.profile_dir / f"place_{slip.date}_leg_{leg.fixture.id}_notfound.png"))
                        return Receipt(False, error=f"leg not found on site: {leg.fixture.home} vs {leg.fixture.away} @ {leg.odds}")

                    _human_delay(0.5, 1.0)
                    # verify betslip count increased
                    try:
                        # betslip badge usually shows count
                        page.wait_for_selector("text=Betslip", timeout=5000)
                    except Exception:
                        pass

                # verify total odds
                try:
                    body_text = page.content()
                    # extract displayed total odds like "2.00" near "Total odds"
                    m = re.search(r"Total[^0-9]*([0-9]+\.[0-9]+)", body_text)
                    if m:
                        displayed = float(m.group(1))
                        if abs(displayed - slip.total_odds) > 0.05:
                            page.screenshot(path=str(self.profile_dir / f"place_{slip.date}_odds_mismatch.png"))
                            return Receipt(False, error=f"odds mismatch: slip {slip.total_odds:.2f} vs site {displayed:.2f}")
                except Exception:
                    pass

                # stake input
                try:
                    stake_sel = "input[placeholder*='Stake' i], input[name*='stake' i], input[type='number']"
                    stake_input = page.locator(stake_sel).first
                    if stake_input.count() > 0:
                        stake_input.click()
                        stake_input.fill("")
                        _human_delay(0.1, 0.3)
                        stake_input.fill(str(int(slip.stake)))
                        _human_delay(0.3, 0.6)
                except Exception as e:
                    return Receipt(False, error=f"stake input not found: {e}")

                # screenshot before place
                pre_path = self.profile_dir / f"place_{slip.date}_pre.png"
                page.screenshot(path=str(pre_path), full_page=True)

                if dry_run:
                    return Receipt(True, bet_id=f"DRY-{slip.date}", screenshot=open(pre_path, "rb").read() if pre_path.exists() else None)

                # click Place Bet
                placed = False
                for sel in ["button:has-text('Place Bet')", "button:has-text('Bet')", "text=Place Bet"]:
                    loc = page.locator(sel)
                    if loc.count() > 0 and loc.first.is_enabled():
                        loc.first.click()
                        placed = True
                        break
                if not placed:
                    return Receipt(False, error="Place Bet button not found/enabled")

                _human_delay(1.0, 2.0)
                # wait for confirmation
                try:
                    page.wait_for_selector("text=Bet placed", timeout=10000)
                except Exception:
                    pass

                # try to extract bet ID
                bet_id = None
                try:
                    content = page.content()
                    m2 = re.search(r"Bet ID[:\s]*([A-Za-z0-9\-]+)", content)
                    if m2:
                        bet_id = m2.group(1).strip()
                    else:
                        m3 = re.search(r"bet[_-]?id[^0-9A-Za-z]*([0-9]+)", content, re.I)
                        if m3:
                            bet_id = m3.group(1)
                except Exception:
                    pass

                post_path = self.profile_dir / f"place_{slip.date}_post.png"
                page.screenshot(path=str(post_path), full_page=True)
                screenshot_bytes = open(post_path, "rb").read() if post_path.exists() else None

                if bet_id:
                    return Receipt(True, bet_id=bet_id, screenshot=screenshot_bytes)
                # even without bet_id, if we saw confirmation, treat as success
                if page.locator("text=Bet placed").count() > 0:
                    return Receipt(True, bet_id=f"OK-{slip.date}", screenshot=screenshot_bytes)
                return Receipt(False, error="no confirmation after Place Bet", screenshot=screenshot_bytes)

            finally:
                try:
                    context.close()
                    browser.close()
                except Exception:
                    pass

    def abort(self) -> None:
        pass
