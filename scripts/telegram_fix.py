import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
from sureodds.config import apply_dotenv, load_config
apply_dotenv()
cfg = load_config("config.yaml")
import httpx
from sureodds.storage import db as dbmod
from sureodds.storage import repo
from sureodds.core.models import SlipStatus

conn = dbmod.connect(cfg.db_path)
dbmod.migrate(conn)
tok = cfg.env["TELEGRAM_BOT_TOKEN"]
cid = cfg.env["TELEGRAM_CHAT_ID"]

def handle_callback(data: str):
    print(f"[handler] data={data}")
    if data.startswith("validate:"):
        sid = int(data.split(":")[1])
        from sureodds.orchestrator import validate_slip
        status = validate_slip(conn, sid, True)
        print(f" -> slip {sid} {status}")
        return status
    if data.startswith("reject:"):
        sid = int(data.split(":")[1])
        from sureodds.orchestrator import validate_slip
        status = validate_slip(conn, sid, False)
        print(f" -> slip {sid} {status}")
        return status
    return None

def handle_message(text: str):
    txt = text.lower().strip()
    # find latest pending slip
    row = conn.execute("SELECT id FROM slips WHERE status='PENDING' ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        print("no pending slip")
        return
    sid = row["id"]
    if any(k in txt for k in ["validate", "place", "yes", "oui"]):
        from sureodds.orchestrator import validate_slip
        status = validate_slip(conn, sid, True)
        print(f"message '{text}' -> slip {sid} {status}")
        return status
    if any(k in txt for k in ["skip", "reject", "no", "non"]):
        from sureodds.orchestrator import validate_slip
        status = validate_slip(conn, sid, False)
        print(f"message '{text}' -> slip {sid} {status}")
        return status

with httpx.Client(timeout=30) as c:
    r = c.get(f"https://api.telegram.org/bot{tok}/getUpdates", params={"timeout": 1})
    j = r.json()
    results = j.get("result", [])
    print(f"pending {len(results)} updates")
    max_id = -1
    for u in results:
        max_id = max(max_id, u["update_id"])
        if "callback_query" in u:
            cb = u["callback_query"]
            data = cb.get("data", "")
            res = handle_callback(data)
            # answer callback
            try:
                c.post(f"https://api.telegram.org/bot{tok}/answerCallbackQuery", json={"callback_query_id": cb["id"], "text": f"Slip {res}" if res else "ok"})
            except Exception as e:
                print(f"answer err {e}")
            # also send confirmation message
            if res:
                try:
                    c.post(f"https://api.telegram.org/bot{tok}/sendMessage", json={"chat_id": cid, "text": f"Slip #{cb.get('data','').split(':')[1]} -> {res}"})
                except Exception as e:
                    print(e)
        elif "message" in u:
            msg = u["message"]
            text = msg.get("text", "")
            print(f"message text: {text!r}")
            res = handle_message(text)
            if res:
                sid = conn.execute("SELECT id FROM slips WHERE status IN ('VALIDATED','REJECTED') ORDER BY id DESC LIMIT 1").fetchone()["id"]
                try:
                    c.post(f"https://api.telegram.org/bot{tok}/sendMessage", json={"chat_id": cid, "text": f"Slip #{sid} -> {res} (from message '{text}')"})
                except Exception as e:
                    print(e)
    if max_id >= 0:
        # ack
        with httpx.Client(timeout=10) as c2:
            c2.get(f"https://api.telegram.org/bot{tok}/getUpdates", params={"offset": max_id+1, "timeout": 1})
        print(f"acked up to {max_id}")

# show current pending/validated
rows = conn.execute("SELECT id,status FROM slips ORDER BY id DESC LIMIT 5").fetchall()
for r in rows:
    print(f"slip #{r['id']} {r['status']}")
