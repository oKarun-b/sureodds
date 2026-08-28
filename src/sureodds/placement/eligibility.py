from __future__ import annotations

from pathlib import Path

from ..core.models import Slip


def scrape_eligible_fixtures(day: str, profile_dir: str | Path = "profiles/betpawa") -> set[int]:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        return set()

    # For now, return empty set — caller will treat all legs as non-2UP if scrape fails.
    # Full scrape would visit betpawa.cm, toggle "Show 1UP & 2UP", and collect fixture keys.
    # This is a lightweight stub that keeps the pipeline working without a browser.
    # To enable, run a headed scrape and map site fixture keys to internal IDs by team names.
    del day, profile_dir
    return set()
