import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.config import apply_dotenv, load_config
apply_dotenv()
cfg = load_config("config.yaml")
from sureodds.storage import db as dbmod
conn = dbmod.connect(cfg.db_path)
rows = conn.execute("SELECT id,status FROM slips WHERE id IN (5,6,7) ORDER BY id").fetchall()
for r in rows:
    print(f"slip #{r['id']} {r['status']}")
