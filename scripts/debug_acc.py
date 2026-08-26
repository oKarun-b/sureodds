from pathlib import Path
import sys
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.config import load_config
from sureodds.storage import db as dbmod, repo
from sureodds.orchestrator import historical_matches
from sureodds.core.ratings import league_averages, team_ratings
from sureodds.core.blend import evaluate_candidates
from sureodds.core.accumulator import build_slip
from datetime import datetime
from zoneinfo import ZoneInfo

cfg = load_config("config.yaml")
conn = dbmod.connect(cfg.db_path)
dbmod.migrate(conn)
today = datetime.now(ZoneInfo(cfg.timezone)).date().isoformat()
fixtures = repo.fixtures_for_date(conn, today)
quotes = repo.quotes_for_date(conn, today)
hist = historical_matches(conn)
avg_h, avg_a = league_averages(hist, cfg.ratings.half_life_days)
rt = team_ratings(hist, cfg.ratings.half_life_days, cfg.ratings.prior_matches)
cands = evaluate_candidates(fixtures, quotes, rt, avg_h, avg_a, cfg)
print(f"cands {len(cands)}")
for c in cands[:10]:
    print(f"  {c.fixture.home[:12]:12} vs {c.fixture.away[:12]:12}  {c.side.value:4} odds {c.odds:.2f} eff {c.eff_p:.2%} blend {c.blended_p:.2%} model {c.model_p:.2%}")

slip = build_slip(cands, cfg, today)
print("slip", slip)
if slip:
    print(f"total {slip.total_odds:.3f} joint {slip.eff_joint_p:.3%} bonus {slip.bonus_pct}")
else:
    # brute check all pairs
    for i in range(len(cands)):
        for j in range(i+1,len(cands)):
            if cands[i].fixture.id==cands[j].fixture.id: continue
            prod=cands[i].odds*cands[j].odds
            if 1.95 <= prod <= 2.05:
                print(f"PAIR {cands[i].odds:.2f}*{cands[j].odds:.2f}={prod:.3f}  {cands[i].fixture.home} vs {cands[j].fixture.home}")
    for i in range(len(cands)):
        for j in range(i+1,len(cands)):
            for k in range(j+1,len(cands)):
                ids={cands[i].fixture.id,cands[j].fixture.id,cands[k].fixture.id}
                if len(ids)!=3: continue
                prod=cands[i].odds*cands[j].odds*cands[k].odds
                if 1.95 <= prod <= 2.05:
                    print(f"TRIPLE {prod:.3f}")
