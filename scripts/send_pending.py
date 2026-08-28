import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.config import apply_dotenv, load_config
apply_dotenv()
cfg = load_config("config.yaml")
from sureodds.storage import db as dbmod, repo
conn = dbmod.connect(cfg.db_path)
row = conn.execute("SELECT id FROM slips WHERE status='PENDING' ORDER BY id DESC LIMIT 1").fetchone()
if row:
    sid = row["id"]
    from sureodds.orchestrator import format_card
    slip = repo._row_slip(conn.execute("SELECT * FROM slips WHERE id=?", (sid,)).fetchone())
    card = format_card(sid, slip, "live 09:00 window 2026-08-29, 2.00 target (best available 1.87)")
    print(card)
    from sureodds.notify.telegram import Telegram
    tok = cfg.env["TELEGRAM_BOT_TOKEN"]
    cid = cfg.env["TELEGRAM_CHAT_ID"]
    t = Telegram(tok, cid)
    t.send_pick(card, sid)
    print(f"sent slip {sid} to Telegram")
else:
    print("no pending")
