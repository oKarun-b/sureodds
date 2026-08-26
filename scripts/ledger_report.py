import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.storage import db as dbmod, repo
from sureodds.config import load_config
cfg = load_config("config.yaml")
conn = dbmod.connect(cfg.db_path)
rows = conn.execute("SELECT id,ts,kind,bankroll_before,delta,bankroll_after,ref FROM ledger ORDER BY id").fetchall()
for r in rows:
    print(f"#{r['id']:02d} {r['kind']:16} {r['bankroll_before']:7.2f} -> {r['bankroll_after']:7.2f}  delta {r['delta']:+7.2f}  ref={r['ref']}  {r['ts'][:19]}")
print("---")
print(f"bankroll now: {repo.get_bankroll(conn,0):.2f} FCFA")
state = repo.load_governor(conn)
print(f"governor: mode={state.mode.value} consec_losses={state.consec_losses} demoted={state.demoted} wm={state.high_watermark:.2f} tier_idx={state.tier_idx}")
print("pending slips today:", conn.execute("SELECT COUNT(*) FROM slips WHERE status='PENDING'").fetchone()[0])
pend = conn.execute("SELECT id,date,total_odds,stake,status FROM slips WHERE status='PENDING'").fetchall()
for p in pend:
    print(f"  pending #{p['id']} {p['date']} {p['total_odds']} stake {p['stake']} {p['status']}")
