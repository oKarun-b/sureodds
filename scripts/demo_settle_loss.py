from pathlib import Path
import sys
sys.path.insert(0, str(Path("src").resolve()))
from datetime import datetime, timezone
from sureodds.config import load_config
from sureodds.storage import db as dbmod, repo
from sureodds.core.models import Side
from sureodds.core.settlement import leg_outcome, settle
from sureodds.core.staking import update_after_result
from sureodds.core.models import Settlement

cfg = load_config("config.yaml")
conn = dbmod.connect(cfg.db_path)
slip_id=4
row=conn.execute("SELECT * FROM slips WHERE id=?",(slip_id,)).fetchone()
print(f"Settling LOSS for slip #{slip_id} stake={row['stake']} odds={row['total_odds']}")
# both HOME bets: first wins 2-0, second loses 0-1 without 2UP => overall LOSS, via flag false (first win no via, second loss no via)
r1=leg_outcome(2,0,Side.HOME,False)
r2=leg_outcome(0,1,Side.HOME,False)
print(f"  {r1} {r2}")
result,payout,bonus,via=settle([r1,r2], stake=float(row["stake"]), total_odds=float(row["total_odds"]), bonus_pct=float(row["bonus_pct"]))
print(f"  result={result} payout={payout} via={via}")
before=repo.get_bankroll(conn,2000.0)
after=repo.ledger_record(conn,"bet_settlement",before,payout-float(row["stake"]),ref=str(slip_id))
print(f"  bankroll {before:.2f} -> {after:.2f}  delta {payout-float(row['stake']):+.2f}")
repo.save_settlement(conn, Settlement(slip_id,result,via,payout,bonus,datetime.now(timezone.utc).isoformat(timespec="seconds")))
state=repo.load_governor(conn)
new_state=update_after_result(state,won=(result=="WIN"),bankroll_now=after,cfg=cfg)
repo.save_governor(conn,new_state)
print(f"  governor {state.mode.value} consec {state.consec_losses} demoted {state.demoted} -> {new_state.mode.value} consec {new_state.consec_losses} demoted {new_state.demoted} wm {new_state.high_watermark}")
conn.execute("UPDATE fixtures SET status='FT', home_goals=2, away_goals=0 WHERE id=300")
conn.execute("UPDATE fixtures SET status='FT', home_goals=0, away_goals=1 WHERE id=301")
conn.commit()
