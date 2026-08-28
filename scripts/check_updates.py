import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").resolve()))
from sureodds.config import apply_dotenv, load_config
apply_dotenv()
cfg = load_config("config.yaml")
tok = cfg.env["TELEGRAM_BOT_TOKEN"]
import httpx
with httpx.Client(timeout=20) as c:
    r = c.get(f"https://api.telegram.org/bot{tok}/getUpdates", params={"timeout": 1})
    j = r.json()
    print(f"pending {len(j.get('result',[]))}")
    for u in j.get("result", []):
        print(u)
