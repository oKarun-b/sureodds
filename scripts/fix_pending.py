import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.config import apply_dotenv, load_config
apply_dotenv()
cfg = load_config("config.yaml")
tok = cfg.env["TELEGRAM_BOT_TOKEN"]
cid = cfg.env["TELEGRAM_CHAT_ID"]
import httpx
from sureodds.storage import db as dbmod
from sureodds.storage import repo
conn = dbmod.connect(cfg.db_path)
with httpx.Client(timeout=20) as c:
    r = c.get(f"https://api.telegram.org/bot{tok}/getUpdates", params={"timeout": 1})
    j = r.json()
    print(f"pending {len(j.get('result',[]))}")
    max_id = -1
    for u in j.get("result", []):
        max_id = max(max_id, u["update_id"])
        if "callback_query" in u:
            cb = u["callback_query"]
            data = cb.get("data","")
            print(f"callback {data}")
            # handle
            if data.startswith("validate:"):
                sid = int(data.split(":")[1])
                from sureodds.orchestrator import validate_slip
                status = validate_slip(conn, sid, True)
                print(f" -> slip {sid} {status}")
                try:
                    c.post(f"https://api.telegram.org/bot{tok}/answerCallbackQuery", json={"callback_query_id": cb["id"], "text": status})
                    c.post(f"https://api.telegram.org/bot{tok}/sendMessage", json={"chat_id": cid, "text": f"Slip #{sid} -> {status}"})
                except Exception as e:
                    print(f"send err {e}")
            elif data.startswith("reject:"):
                sid = int(data.split(":")[1])
                from sureodds.orchestrator import validate_slip
                status = validate_slip(conn, sid, False)
                print(f" -> slip {sid} {status}")
                try:
                    c.post(f"https://api.telegram.org/bot{tok}/answerCallbackQuery", json={"callback_query_id": cb["id"], "text": status})
                    c.post(f"https://api.telegram.org/bot{tok}/sendMessage", json={"chat_id": cid, "text": f"Slip #{sid} -> {status}"})
                except Exception as e:
                    print(f"send err {e}")
        elif "message" in u:
            txt = u["message"].get("text","")
            print(f"message {txt!r}")
    if max_id >= 0:
        # ack
        with httpx.Client(timeout=10) as c2:
            c2.get(f"https://api.telegram.org/bot{tok}/getUpdates", params={"offset": max_id+1, "timeout": 1})
        print(f"acked {max_id}")
# show slips
rows = conn.execute("SELECT id,status FROM slips ORDER BY id DESC LIMIT 5").fetchall()
for r in rows:
    print(f"slip #{r['id']} {r['status']}")
