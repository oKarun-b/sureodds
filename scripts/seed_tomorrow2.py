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
# wipe
conn.execute("DELETE FROM snapshots WHERE fixture_id IN (SELECT id FROM fixtures WHERE date=?)", (tomorrow,))
conn.execute("DELETE FROM slips WHERE date=?", (tomorrow,))
conn.execute("DELETE FROM fixtures WHERE date=?", (tomorrow,))
conn.commit()
random.seed(123)
teams = [("Alpha FC","Beta United",1.33),("Gamma SC","Theta Town",1.47),("Delta City","Epsilon Rovers",1.34),("Alpha FC","Zeta Athletic",1.46),("Gamma SC","Eta FC",1.32),("Epsilon Rovers","Zeta Athletic",1.45)]
books = [f"Book{i:02d}" for i in range(1,13)]
fixtures=[]
quotes=[]
fid=300
for h,a,ho in teams:
    fixtures.append(Fixture(id=fid, date=tomorrow, league="Cameroon - Elite One", home=h, away=a, kickoff=tomorrow + " 18:00:00+01:00", status="NS"))
    for b in books:
        dr = round(random.uniform(4.0,5.2),2)
        ar = round(random.uniform(6.5,9.0),2)
        quotes.append(Quote(fixture_id=fid, bookmaker=b, ts=tomorrow+"T08:00:00+01:00", home_o=ho, draw_o=dr, away_o=ar))
    fid+=1
repo.upsert_fixtures(conn, fixtures)
repo.save_quotes(conn, quotes)
print(f"reinserted {len(fixtures)} fixtures + {len(quotes)} quotes for {tomorrow}")
