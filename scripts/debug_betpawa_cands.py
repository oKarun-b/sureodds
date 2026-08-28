import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.storage import db as dbmod
from sureodds.config import load_config, apply_dotenv
apply_dotenv()
cfg = load_config("config.yaml")
conn = dbmod.connect(cfg.db_path)
from sureodds.orchestrator import window_for_day, _fixture_in_window, historical_matches
from sureodds.core.ratings import league_averages, team_ratings
from sureodds.core.blend import evaluate_candidates
from datetime import datetime
from zoneinfo import ZoneInfo

today = "2026-08-29"
start,end = window_for_day(cfg, today)
from sureodds.storage import repo
all_fx=[]
for d in {start.astimezone(ZoneInfo(cfg.timezone)).date().isoformat(), end.astimezone(ZoneInfo(cfg.timezone)).date().isoformat()}:
    all_fx.extend(repo.fixtures_for_date(conn, d))
filtered=[fx for fx in all_fx if _fixture_in_window(fx, start, end)]
if cfg.betpawa.leagues:
    filtered=[fx for fx in filtered if fx.league in cfg.betpawa.leagues]
print(f"filtered {len(filtered)} in window and allowlist")
# get quotes for those fixtures
quotes={}
for fid in [fx.id for fx in filtered]:
    qs=conn.execute("SELECT * FROM snapshots WHERE fixture_id=?", (fid,)).fetchall()
    if qs:
        from sureodds.core.models import Quote
        quotes[fid]=[Quote(fixture_id=r["fixture_id"], bookmaker=r["bookmaker"], ts=r["ts"], home_o=r["home_o"], draw_o=r["draw_o"], away_o=r["away_o"]) for r in qs]
print(f"quotes groups with data: {len(quotes)}")
# try evaluate with current cfg
from sureodds.core.ratings import HistoricalMatch
hist=historical_matches(conn)
print(f"hist {len(hist)}")
if len(hist)>=30:
    avg_h, avg_a = league_averages(hist, cfg.ratings.half_life_days)
    rt=team_ratings(hist, cfg.ratings.half_life_days, cfg.ratings.prior_matches)
    print(f"avg {avg_h:.2f}/{avg_a:.2f} teams {len(rt)}")
    cands=evaluate_candidates(filtered, quotes, rt, avg_h, avg_a, cfg)
    print(f"cands {len(cands)}")
    for c in cands[:5]:
        print(f"  {c.fixture.league} {c.fixture.home} vs {c.fixture.away} {c.side.value} {c.odds:.2f} model {c.model_p:.2%} cons {c.consensus_p:.2%}")
    # also show why others fail: for each filtered fixture, show model/cons and gate
    from sureodds.core.poisson import predict_match
    from sureodds.core.ratings import goal_expectations
    from sureodds.core.blend import consensus
    for fx in filtered[:5]:
        qs=quotes.get(fx.id, [])
        if not qs: 
            print(f"  {fx.league} no quotes")
            continue
        from sureodds.core.blend import consensus as cons_fn
        cons=cons_fn(qs)
        if not cons:
            print(f"  {fx.league} no cons")
            continue
        lh,la=goal_expectations(rt, fx.home, fx.away, avg_h, avg_a)
        _, probs=predict_match(lh, la)
        print(f"  {fx.league} {fx.home} vs {fx.away} lh {lh:.2f} la {la:.2f} probs {probs} cons {cons.probs} best {cons.best_odds}")
else:
    print("not enough hist")
