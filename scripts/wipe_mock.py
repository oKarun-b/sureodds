import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.storage import db as dbmod
from sureodds.config import load_config, apply_dotenv
apply_dotenv()
cfg = load_config("config.yaml")
conn = dbmod.connect(cfg.db_path)
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
today = datetime.now(ZoneInfo(cfg.timezone)).date().isoformat()
tomorrow_str = (datetime.now(ZoneInfo(cfg.timezone)).date() + timedelta(days=1)).isoformat()
for d in [today, tomorrow_str]:
    cnt = conn.execute("SELECT COUNT(*) FROM fixtures WHERE date=? AND id<10000", (d,)).fetchone()[0]
    print(f"{d} mocked fixtures {cnt}")
    conn.execute("DELETE FROM snapshots WHERE fixture_id IN (SELECT id FROM fixtures WHERE date=? AND id<10000)", (d,))
    conn.execute("DELETE FROM fixtures WHERE date=? AND id<10000", (d,))
    conn.commit()
    print(f"wiped {d}")
conn.execute("DELETE FROM slips WHERE date=? AND status='PENDING'", (today,))
# keep settlements history; don't delete snapshots for already-settled historical fixtures
conn.commit()
print("slips remaining", conn.execute("SELECT COUNT(*) FROM slips").fetchone()[0])
print("fixtures today now", conn.execute("SELECT COUNT(*) FROM fixtures WHERE date=?", (today,)).fetchone()[0])
