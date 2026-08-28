import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.storage import db as dbmod
from sureodds.config import load_config, apply_dotenv
apply_dotenv()
cfg = load_config("config.yaml")
conn = dbmod.connect(cfg.db_path)
rows = conn.execute("SELECT id, date, status, stake, total_odds FROM slips ORDER BY id").fetchall()
for r in rows:
    print(f"#{r['id']:02d} {r['date']} {r['status']:9} stake {r['stake']} odds {r['total_odds']}")
print("--- settlements ---")
rows2 = conn.execute("SELECT slip_id, result, via_2up, payout FROM settlements ORDER BY slip_id").fetchall()
for r in rows2:
    print(f"slip {r['slip_id']} {r['result']} via2up={bool(r['via_2up'])} payout {r['payout']}")
print("--- pending ---")
pend = conn.execute("SELECT id, status FROM slips WHERE status='PENDING'").fetchall()
for r in pend:
    print(f"pending #{r['id']}")
