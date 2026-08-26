from pathlib import Path
import sys
sys.path.insert(0, str(Path("src").resolve()))

from sureodds.config import load_config
from sureodds.storage import db as dbmod
from sureodds.storage import repo
from sureodds.core.ratings import HistoricalMatch, league_averages, team_ratings, goal_expectations
from sureodds.core.poisson import predict_match
from sureodds.core.blend import consensus
from datetime import datetime
from zoneinfo import ZoneInfo

cfg = load_config("config.yaml")
conn = dbmod.connect(cfg.db_path)
dbmod.migrate(conn)
from sureodds.orchestrator import historical_matches
today = datetime.now(ZoneInfo(cfg.timezone)).date().isoformat()
print("today", today)
fixtures = repo.fixtures_for_date(conn, today)
quotes = repo.quotes_for_date(conn, today)
print(f"fixtures {len(fixtures)} keys {list(quotes.keys())[:3]}")
hist = historical_matches(conn)
print(f"hist {len(hist)}")
if len(hist)>=30:
    avg_h, avg_a = league_averages(hist, cfg.ratings.half_life_days)
    rt = team_ratings(hist, cfg.ratings.half_life_days, cfg.ratings.prior_matches)
    print(f"avg_h {avg_h:.3f} avg_a {avg_a:.3f}")
    for fx in fixtures[:3]:
        lh, la = goal_expectations(rt, fx.home, fx.away, avg_h, avg_a)
        m, probs = predict_match(lh, la, max_goals=cfg.ratings.max_goals)
        print(f"{fx.home} vs {fx.away}  lam {lh:.2f}/{la:.2f}  probs {probs}")
        qs = quotes.get(fx.id, [])
        if qs:
            c = consensus(qs)
            print(f"  consensus {c.probs} best {c.best_odds} n={c.n_books}")
            for side in ["HOME","DRAW","AWAY"]:
                import sureodds.core.models as mod
                s = mod.Side(side)
                print(f"    {side}: odds {c.best_odds[s]:.2f} cons {c.probs[s]:.2%} model {probs[side]:.2%} blended {cfg.blend.w_model*probs[side]+(1-cfg.blend.w_model)*c.probs[s]:.2%}")
else:
    print("not enough hist")
