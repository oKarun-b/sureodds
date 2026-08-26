from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sureodds.config import load_config
from sureodds.core.models import Fixture, Quote
from sureodds.storage import db as dbmod
from sureodds.storage import repo

random.seed(42)

cfg = load_config(ROOT / "config.yaml")
conn = dbmod.connect(cfg.db_path)
dbmod.migrate(conn)

today = datetime.now(ZoneInfo(cfg.timezone)).date().isoformat()
print(f"[seed] today={today} tz={cfg.timezone}")

# reset bankroll + governor for clean demo
repo.meta_set(conn, "bankroll", "2000")
import json
from sureodds.core.models import GovernorMode, GovernorState

repo.save_governor(conn, GovernorState(mode=GovernorMode.PAPER_FLOOR, tier_idx=0, demoted=False, consec_losses=0, high_watermark=2000.0))
print("[seed] bankroll reset to 2000 FCFA, governor clean")

# wipe today's data for idempotency
conn.execute("DELETE FROM snapshots WHERE fixture_id IN (SELECT id FROM fixtures WHERE date = ?)", (today,))
conn.execute("DELETE FROM slips WHERE date = ?", (today,))
conn.execute("DELETE FROM fixtures WHERE date = ?", (today,))
conn.commit()

# 1) historical finished fixtures for ratings context (past 60 days, ~40 matches)
teams = ["Alpha FC", "Beta United", "Gamma SC", "Delta City", "Epsilon Rovers", "Zeta Athletic", "Eta FC", "Theta Town"]
hist = []
base_date = datetime.now(ZoneInfo(cfg.timezone)).date()
fid_seq = 9000
for i in range(40):
    d = (base_date - timedelta(days=random.randint(5, 60))).isoformat()
    home = random.choice(teams)
    away = random.choice([t for t in teams if t != home])
    # make Alpha/Gamma/Delta stronger at home on average
    bias = 0.7 if home in ("Alpha FC", "Gamma SC", "Delta City") else -0.2
    hg = max(0, int(random.gauss(1.8 + bias, 1.0)))
    ag = max(0, int(random.gauss(1.1 - bias * 0.5, 0.9)))
    hg = min(hg, 5); ag = min(ag, 4)
    fid_seq += 1
    hist.append(Fixture(id=fid_seq, date=d, league="Cameroon - Elite One", home=home, away=away, kickoff=f"{d} 15:00", status="FT", home_goals=hg, away_goals=ag))
repo.upsert_fixtures(conn, hist)
print(f"[seed] inserted {len(hist)} historical FT fixtures")

# 2) today's fixtures (12 matches, all 18:00, include our strong homes as favorites)
todays = []
quotes_to_save: list[Quote] = []
today_fixtures = [
    ("Alpha FC", "Beta United"),
    ("Gamma SC", "Theta Town"),
    ("Delta City", "Epsilon Rovers"),
    ("Alpha FC", "Zeta Athletic"),
    ("Gamma SC", "Eta FC"),
    ("Delta City", "Beta United"),
    ("Epsilon Rovers", "Zeta Athletic"),
    ("Eta FC", "Theta Town"),
    ("Alpha FC", "Epsilon Rovers"),
    ("Gamma SC", "Zeta Athletic"),
    ("Delta City", "Theta Town"),
    ("Beta United", "Eta FC"),
]
kick = f"{today} 18:00:00+01:00"
for idx, (h, a) in enumerate(today_fixtures, start=1):
    fid = 100 + idx
    todays.append(Fixture(id=fid, date=today, league="Cameroon - Elite One", home=h, away=a, kickoff=kick, status="NS"))
repo.upsert_fixtures(conn, todays)
print(f"[seed] inserted {len(todays)} fixtures for {today}")

# 3) quotes: 12 bookmakers per fixture, all inside leg band [1.20,1.60] for the favorite side
# Make home the favorite for our strong homes (odds 1.24-1.45), draw ~4.2-5.5, away 6-9
books = [f"Book{i:02d}" for i in range(1, 13)]
for fx in todays:
    is_strong_home = fx.home in ("Alpha FC", "Gamma SC", "Delta City")
    if is_strong_home:
        base_home = random.uniform(1.24, 1.42)
    else:
        # more balanced -> home still slight favorite but lower prob
        base_home = random.uniform(1.45, 1.58)
    for b in books:
        jitter = random.uniform(-0.06, 0.06)
        home_o = round(max(1.20, min(1.60, base_home + jitter)), 2)
        draw_o = round(random.uniform(3.9, 5.4), 2)
        away_o = round(random.uniform(6.0, 9.5), 2)
        # ensure favorite odds stay in band after jitter
        if not (1.20 <= home_o <= 1.60):
            home_o = round(base_home, 2)
        quotes_to_save.append(Quote(fixture_id=fx.id, bookmaker=b, ts=f"{today}T08:00:00+01:00", home_o=home_o, draw_o=draw_o, away_o=away_o))
    # add 2UP eligibility for half the fixtures (simulate BetPawa 1X2 2UP market)
repo.save_quotes(conn, quotes_to_save)
print(f"[seed] inserted {len(quotes_to_save)} quote rows ({len(books)} books × {len(todays)} fixtures)")

# quick sanity: ensure at least params pass filters
import json as _json
print(f"[seed] done — bankroll={repo.get_bankroll(conn, 0)} FCFA, fixtures today={len(repo.fixtures_for_date(conn, today))}, quotes groups={len(repo.quotes_for_date(conn, today))}")
