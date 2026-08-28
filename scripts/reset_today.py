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
# delete rejected for today
cnt = conn.execute("SELECT COUNT(*) FROM slips WHERE date=? AND status='REJECTED'", (today,)).fetchone()[0]
print(f"today {today} rejected {cnt}")
conn.execute("DELETE FROM slips WHERE date=? AND status='REJECTED'", (today,))
conn.commit()
print("deleted rejected for today, remaining slips:")
rows = conn.execute("SELECT id, date, status FROM slips ORDER BY id").fetchall()
for r in rows:
    print(f"#{r['id']} {r['date']} {r['status']}")
