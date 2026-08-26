from pathlib import Path
import sys, random
sys.path.insert(0, str(Path("src").resolve()))
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sureodds.config import load_config
from sureodds.storage import db as dbmod, repo
from sureodds.core.models import Fixture, Quote

cfg = load_config("config.yaml")
conn = dbmod.connect(cfg.db_path)
tomorrow = (datetime.now(ZoneInfo(cfg.timezone)).date() + timedelta(days=1)).isoformat()
print(f"[seed] tomorrow={tomorrow}")

# create 8 fixtures for tomorrow, reusing teams
teams_tom = [("Delta City","Beta United"),("Alpha FC","Theta Town"),("Gamma SC","Epsilon Rovers"),("Eta FC","Zeta Athletic")]
random.seed(123)
fid_base=200
todays=[]
for i,(h,a) in enumerate(teams_tom):
    fid=fid_base+i
    todays.append(Fixture(id=fid, date=tomorrow, league="Cameroon - Elite One", home=h, away=a, kickoff=f"{tomorrow} 18:00:00+01:00", status="NS"))
repo.upsert_fixtures(conn, todays)
# quotes: mix to ensure band
books=[f"Book{i:02d}" for i in range(1,13)]
mapping={200:1.33,201:1.46,202:1.34,203:1.45}
quotes=[]
for fid,ho in mapping.items():
    for b in books:
        quotes.append(Quote(fixture_id=fid, bookmaker=b, ts=f"{tomorrow}T08:00:00+01:00", home_o=ho, draw_o=round(random.uniform(4.0,5.2),2), away_o=round(random.uniform(6.5,9.0),2)))
repo.save_quotes(conn, quotes)
print(f"[seed] inserted {len(todays)} fixtures + {len(quotes)} quotes for {tomorrow}")
