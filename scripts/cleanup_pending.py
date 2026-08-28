import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.storage import db as dbmod
from sureodds.config import load_config, apply_dotenv
apply_dotenv()
cfg = load_config("config.yaml")
conn = dbmod.connect(cfg.db_path)
from datetime import datetime
from zoneinfo import ZoneInfo
today = datetime.now(ZoneInfo(cfg.timezone)).date().isoformat()
cnt = conn.execute("SELECT COUNT(*) FROM slips WHERE date=? AND status='PENDING'", (today,)).fetchone()[0]
print(f"today {today} pending {cnt}")
# keep only latest pending, delete older pending for today
rows = conn.execute("SELECT id FROM slips WHERE date=? AND status='PENDING' ORDER BY id", (today,)).fetchall()
if len(rows) > 1:
    for r in rows[:-1]:
        conn.execute("DELETE FROM slips WHERE id=?", (r["id"],))
        print(f"deleted pending #{r['id']}")
    conn.commit()
print("remaining pending:", conn.execute("SELECT id FROM slips WHERE status='PENDING'").fetchall())
