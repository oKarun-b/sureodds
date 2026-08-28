import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.storage import db as dbmod
from sureodds.config import load_config, apply_dotenv
apply_dotenv()
cfg = load_config("config.yaml")
conn = dbmod.connect(cfg.db_path)
today = "2026-08-29"
cnt = conn.execute("SELECT COUNT(*) FROM slips WHERE date=? AND status='PENDING'", (today,)).fetchone()[0]
print(f"pending for {today}: {cnt}")
conn.execute("DELETE FROM slips WHERE date=? AND status='PENDING'", (today,))
conn.commit()
print("deleted")
