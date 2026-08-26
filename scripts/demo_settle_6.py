import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from datetime import datetime, timezone
from sureodds.config import apply_dotenv, load_config
apply_dotenv()
cfg = load_config("config.yaml")
from sureodds.storage import db as dbmod, repo
from sureodds.core.models import Side, Settlement
from sureodds.core.settlement import leg_outcome, settle
from sureodds.core.staking import update_after_result
conn = dbmod.connect(cfg.db_path)
sid = 6
row = conn.execute("SELECT * FROM slips WHERE id=?", (sid,)).fetchone()
print(f"Settling slip #{sid} {row['date']} {row['total_odds']} stake {row['stake']}")
# Synthesize: Barcelona 2-0 win, River Plate 2-2 draw but led 2-0 => WIN via 2UP
r1 = leg_outcome(2, 0, Side.HOME, False)
r2 = leg_outcome(2, 2, Side.HOME, True)
print(f"  legs: {r1} {r2}")
result, payout, bonus, via = settle([r1, r2], stake=float(row["stake"]), total_odds=float(row["total_odds"]), bonus_pct=float(row["bonus_pct"]))
print(f"  -> {result} payout {payout} bonus {bonus} via={via}")
before = repo.get_bankroll(conn, 2000.0)
after = repo.ledger_record(conn, "bet_settlement", before, payout - float(row["stake"]), ref=str(sid))
print(f"  bankroll {before:.2f} -> {after:.2f}")
repo.save_settlement(conn, Settlement(sid, result, via, payout, bonus, datetime.now(timezone.utc).isoformat(timespec="seconds")))
state = repo.load_governor(conn)
new_state = update_after_result(state, won=(result=="WIN"), bankroll_now=after, cfg=cfg)
repo.save_governor(conn, new_state)
print(f"  governor {state.mode.value}->{new_state.mode.value} consec {state.consec_losses}->{new_state.consec_losses} demoted {new_state.demoted}")
# mark fixtures FT for history
conn.execute("UPDATE fixtures SET status='FT', home_goals=2, away_goals=0 WHERE id IN (SELECT json_extract(value, '$.fixture_id') FROM json_each((SELECT legs_json FROM slips WHERE id=?)), (SELECT id FROM slips WHERE id=?))", (sid,sid))
# simpler: just update the two known fixture ids from legs_json
import json
legs = json.loads(row["legs_json"])
for leg in legs:
    fid = leg["fixture_id"]
    # set 2-0 for first, 2-2 for second
    if legs.index(leg) == 0:
        conn.execute("UPDATE fixtures SET status='FT', home_goals=2, away_goals=0 WHERE id=?", (fid,))
    else:
        conn.execute("UPDATE fixtures SET status='FT', home_goals=2, away_goals=2 WHERE id=?", (fid,))
conn.commit()
print("  fixtures marked FT")
