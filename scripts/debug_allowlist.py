import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.storage import db as dbmod
from sureodds.config import load_config, apply_dotenv
apply_dotenv()
cfg = load_config("config.yaml")
print("allowlist", cfg.betpawa.leagues)
conn = dbmod.connect(cfg.db_path)
from datetime import datetime
from zoneinfo import ZoneInfo
from sureodds.orchestrator import window_for_day, _fixture_in_window
from sureodds.storage import repo

today = "2026-08-29"
start, end = window_for_day(cfg, today)
print(f"window {start} -> {end}")

all_fx = []
for d in {start.astimezone(ZoneInfo(cfg.timezone)).date().isoformat(), end.astimezone(ZoneInfo(cfg.timezone)).date().isoformat()}:
    all_fx.extend(repo.fixtures_for_date(conn, d))
print(f"all fixtures in DB for window dates {len(all_fx)}")

filtered = [fx for fx in all_fx if _fixture_in_window(fx, start, end)]
print(f"in window {len(filtered)}")
for fx in filtered[:3]:
    try:
        print(f"  {fx.league} {fx.home} vs {fx.away} {fx.kickoff}")
    except UnicodeEncodeError:
        print(f"  {fx.league.encode('ascii','replace')}")

if cfg.betpawa.leagues:
    filtered2 = [fx for fx in filtered if fx.league in cfg.betpawa.leagues]
    print(f"after betpawa filter {len(filtered2)}")
    for fx in filtered2[:3]:
        try:
            print(f"  {fx.league} {fx.home} vs {fx.away}")
        except UnicodeEncodeError:
            print(f"  {fx.league.encode('ascii','replace')}")

quotes = repo.quotes_for_date(conn, "2026-08-29")
print(f"quotes groups for 2026-08-29: {len(quotes)}")
for fid, qs in list(quotes.items())[:3]:
    fx = next((f for f in filtered if f.id == fid), None)
    if fx:
        print(f"  fid {fid} {fx.league} quotes {len(qs)}")
    else:
        print(f"  fid {fid} not in window")
