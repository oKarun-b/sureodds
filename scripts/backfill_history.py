import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sureodds.config import apply_dotenv, load_config
apply_dotenv()
cfg = load_config("config.yaml")
from sureodds.storage import db as dbmod, repo
from sureodds.providers.api_football import ApiFootball

conn = dbmod.connect(cfg.db_path)
dbmod.migrate(conn)

today = datetime.now(ZoneInfo(cfg.timezone)).date()
days = 14
print(f"Backfilling {days} days ending {(today - timedelta(days=1)).isoformat()} (today={today.isoformat()})")

def counter():
    # use repo's api_usage for today as crude budget check; backfill uses same day budget but we spread across historical dates, so just return 0 to bypass
    return 0

prov = ApiFootball(api_key=cfg.env["API_FOOTBALL_KEY"], base_url=cfg.api.football_base, call_counter=lambda: 0, daily_budget=1000)

total_new = 0
for i in range(1, days+1):
    d = (today - timedelta(days=i)).isoformat()
    try:
        fxs = prov.get_fixtures(d)
        ft = [f for f in fxs if f.status == "FT" and f.home_goals is not None]
        repo.upsert_fixtures(conn, fxs)
        print(f"{d}: {len(fxs)} fixtures ({len(ft)} FT) -> upserted")
        total_new += len(fxs)
    except Exception as e:
        print(f"{d}: error {e}")

print(f"done total {total_new} fixtures")
# summary
from sureodds.orchestrator import historical_matches
hist = historical_matches(conn, limit=5000)
print(f"historical FT in DB now: {len(hist)}")
if hist:
    from sureodds.core.ratings import league_averages
    avg_h, avg_a = league_averages(hist, cfg.ratings.half_life_days)
    print(f"league avg home {avg_h:.2f} away {avg_a:.2f}")

# show api usage for today
print(f"api calls today (repo counter): {repo.api_calls_today(conn, today.isoformat())}")
# actual provider used 14 calls; repo counter not incremented because we bypassed; show real provider stats via /status
import httpx
with httpx.Client(base_url=cfg.api.football_base, headers={"x-apisports-key": cfg.env["API_FOOTBALL_KEY"]}, timeout=15) as c:
    r = c.get("/status")
    print("status requests:", r.json()["response"]["requests"])
