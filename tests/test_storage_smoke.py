from __future__ import annotations

import json

from sureodds.core.models import Fixture, Leg, Side, Slip
from sureodds.storage import db as dbmod
from sureodds.storage import repo


def _slip(day="2026-08-26", stake=50.0):
    fx = Fixture(id=101, date=day, league="Test L", home="Alpha", away="Beta", kickoff=f"{day} 18:00")
    leg = Leg(fixture=fx, side=Side.HOME, odds=1.26, model_p=0.7, consensus_p=0.72, blended_p=0.71, eff_p=0.79, eligible_2up=True)
    s = Slip(date=day, legs=[leg])
    s.total_odds = 1.26
    s.joint_p = 0.71
    s.eff_joint_p = 0.79
    s.bonus_pct = 0.0
    s.stake = stake
    s.mode = "GROWTH"
    return s


def test_migrate_and_roundtrip(tmp_path):
    conn = dbmod.connect(tmp_path / "test.db")
    dbmod.migrate(conn, ROOT_MIGRATIONS)

    repo.upsert_fixtures(conn, [_slip().legs[0].fixture])
    day_rows = repo.fixtures_for_date(conn, "2026-08-26")
    assert len(day_rows) == 1

    sid = repo.create_slip(conn, _slip(), "GROWTH")
    pending = repo.latest_pending_slip(conn, "2026-08-26")
    assert pending is not None and pending[0] == sid
    loaded = pending[1]
    assert loaded.total_odds == 1.26
    assert loaded.legs[0].eligible_2up is True

    before = repo.get_bankroll(conn, 1000.0)
    after = repo.ledger_record(conn, "bet_settlement", before, 76.0, ref=str(sid))
    assert after == 1076.0
    assert repo.get_bankroll(conn, 0.0) == 1076.0


ROOT_MIGRATIONS = str(__import__("pathlib").Path(__file__).resolve().parents[1] / "migrations")


def test_governor_and_brier_roundtrip(tmp_path):
    from sureodds.core.models import GovernorMode, Settlement, SlipStatus, GovernorState

    conn = dbmod.connect(tmp_path / "g.db")
    dbmod.migrate(conn, ROOT_MIGRATIONS)

    state = GovernorState(mode=GovernorMode.GROWTH, tier_idx=0, demoted=False, consec_losses=1, high_watermark=1234.5)
    repo.save_governor(conn, state)
    loaded = repo.load_governor(conn)
    assert loaded.mode == GovernorMode.GROWTH
    assert loaded.consec_losses == 1
    assert loaded.high_watermark == 1234.5

    sid = repo.create_slip(conn, _slip(), "GROWTH")
    repo.set_slip_status(conn, sid, SlipStatus.PLACED, bet_id="BET-1")
    repo.save_settlement(conn, Settlement(sid, "WIN", True, 126.0, 6.0, "2026-08-27T08:00:00+00:00"))

    res = repo.recent_settled(conn, 10)
    assert len(res) == 1 and res[0]["won"] is True and res[0]["via_2up"] is True
    assert repo.consecutive_losses(conn) == 0

    brier, n = repo.brier_window(conn, 60)
    assert n == 1 and brier is not None

    unsettled = repo.unsettled_slips_for_date(conn, "2026-09-01")
    assert unsettled == []


def test_api_usage_counter(tmp_path):
    conn = dbmod.connect(tmp_path / "q.db")
    dbmod.migrate(conn, ROOT_MIGRATIONS)
    assert repo.api_calls_today(conn, "2026-08-26") == 0
    repo.api_call_incr(conn, "2026-08-26")
    repo.api_call_incr(conn, "2026-08-26", 3)
    assert repo.api_calls_today(conn, "2026-08-26") == 4
    assert json.loads('{"ok": true}')["ok"]
