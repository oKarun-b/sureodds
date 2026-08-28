import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.storage import db as dbmod
from sureodds.config import load_config, apply_dotenv
apply_dotenv()
cfg = load_config("config.yaml")
conn = dbmod.connect(cfg.db_path)
# get quotes groups for today
from datetime import datetime
from zoneinfo import ZoneInfo
today = "2026-08-29"
# get fixtures for today with quotes
rows = conn.execute("SELECT DISTINCT f.league, f.home, f.away FROM fixtures f JOIN snapshots s ON s.fixture_id=f.id WHERE f.date=?", (today,)).fetchall()
print(f"leagues with odds for {today}:")
leagues = {}
for r in rows:
    leagues[r["league"]] = leagues.get(r["league"], 0) + 1
for league, cnt in sorted(leagues.items()):
    print(f"  {league}: {cnt} fixtures")
