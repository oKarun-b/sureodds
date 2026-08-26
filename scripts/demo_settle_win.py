from pathlib import Path
import sys
sys.path.insert(0, str(Path("src").resolve()))
from datetime import datetime, timezone
from sureodds.config import load_config
from sureodds.storage import db as dbmod, repo
from sureodds.core.models import Side
from sureodds.core.settlement import leg_outcome, settle
from sureodds.core.staking import update_after_result

cfg = load_config("config.yaml")
conn = dbmod.connect(cfg.db_path)
dbmod.migrate(conn)

# synthetic settlement for slip #3: 2 legs, both HOME
# scenario: leg1 2-0 board win, leg2 2-2 draw but HOME had led 2-0 => rescued via 2UP => overall WIN via_2up=True
# This demonstrates the BetPawa 2UP facility in action
slip_id = 3
row = conn.execute("SELECT * FROM slips WHERE id=?", (slip_id,)).fetchone()
print(f"Settling slip #{slip_id}  date={row['date']}  stake={row['stake']}  odds={row['total_odds']}  mode={row['mode']}")

# Build leg results manually
# leg 104: Alpha FC vs Zeta Athletic  -> 2-0
# leg 109: Alpha FC vs Epsilon Rovers -> 2-2 but HOME led 2-0 (ever2up true)
r1 = leg_outcome(2, 0, Side.HOME, ever2up_side=False)  # board win
r2 = leg_outcome(2, 2, Side.HOME, ever2up_side=True)   # draw rescued by 2UP
print(f"  leg1: {r1}  leg2: {r2}")

result, payout, bonus, via = settle([r1, r2], stake=float(row["stake"]), total_odds=float(row["total_odds"]), bonus_pct=float(row["bonus_pct"]))
print(f"  result={result} payout={payout} bonus={bonus} via_2up={via}  EV would have been {(payout-float(row['stake']))/float(row['stake']):+.1%} on this slip")

before = repo.get_bankroll(conn, 2000.0)
after = repo.ledger_record(conn, "bet_settlement", before, payout - float(row["stake"]), ref=str(slip_id))
print(f"  bankroll {before:.2f} -> {after:.2f}  delta {payout-float(row['stake']):+.2f}")

from sureodds.core.models import Settlement
repo.save_settlement(conn, Settlement(slip_id, result, via, payout, bonus, datetime.now(timezone.utc).isoformat(timespec="seconds")))

# update governor
state = repo.load_governor(conn)
new_state = update_after_result(state, won=(result=="WIN"), bankroll_now=after, cfg=cfg)
repo.save_governor(conn, new_state)
print(f"  governor {state.mode.value} consec_losses {state.consec_losses} -> {new_state.mode.value} {new_state.consec_losses} demoted={new_state.demoted}")

# mark fixtures as FT for history
conn.execute("UPDATE fixtures SET status='FT', home_goals=2, away_goals=0 WHERE id=104")
conn.execute("UPDATE fixtures SET status='FT', home_goals=2, away_goals=2 WHERE id=109")
conn.commit()
print("  fixtures marked FT")
