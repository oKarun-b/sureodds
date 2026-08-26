import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.config import apply_dotenv, load_config
apply_dotenv()
cfg = load_config("config.yaml")
from sureodds.storage import db as dbmod, repo
conn = dbmod.connect(cfg.db_path)
pend = conn.execute("SELECT id FROM slips WHERE status='PENDING' ORDER BY id DESC LIMIT 1").fetchone()
print(pend)
if pend:
    sid = pend["id"]
    row = conn.execute("SELECT * FROM slips WHERE id=?", (sid,)).fetchone()
    slip = repo._row_slip(row)
    from sureodds.orchestrator import format_card
    card = format_card(sid, slip, "paper floor: live 344 fixtures, 30 with odds, 3 candidates")
    print(card)
    from sureodds.notify.telegram import Telegram
    tok = cfg.env["TELEGRAM_BOT_TOKEN"]
    cid = cfg.env["TELEGRAM_CHAT_ID"]
    t = Telegram(tok, cid)
    t.send_pick(card, sid)
    print(f"sent slip {sid} to Telegram {cid}")
