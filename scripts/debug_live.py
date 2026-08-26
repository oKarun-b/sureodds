import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.config import load_config
from sureodds.storage import db as dbmod, repo
from sureodds.orchestrator import historical_matches
from sureodds.core.ratings import league_averages, team_ratings
from sureodds.core.blend import evaluate_candidates
from datetime import datetime
from zoneinfo import ZoneInfo
cfg=load_config("config.yaml")
conn=dbmod.connect(cfg.db_path)
today=datetime.now(ZoneInfo(cfg.timezone)).date().isoformat()
fixtures=repo.fixtures_for_date(conn, today)
quotes=repo.quotes_for_date(conn, today)
print(f"today {today} fixtures {len(fixtures)} quote groups {len(quotes)}")
from sureodds.orchestrator import historical_matches
hist=historical_matches(conn)
print(f"hist {len(hist)}")
avg_h, avg_a = (1.4,1.15)
rt={}
if len(hist)>=30:
    from sureodds.core.ratings import league_averages, team_ratings
    avg_h, avg_a = league_averages(hist, cfg.ratings.half_life_days)
    rt = team_ratings(hist, cfg.ratings.half_life_days, cfg.ratings.prior_matches)
    print(f"avg {avg_h:.2f}/{avg_a:.2f} teams {len(rt)}")
else:
    print("using defaults")
# show candidates details
cands = evaluate_candidates(fixtures, quotes, rt, avg_h, avg_a, cfg)
print(f"cands {len(cands)}")
for c in cands[:10]:
    print(f"  {c.fixture.home} vs {c.fixture.away} {c.side.value} odds {c.odds} model {c.model_p:.2%} cons {c.consensus_p:.2%} blend {c.blended_p:.2%}")
# show odds for all cands
