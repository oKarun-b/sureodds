from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from ..core.models import (
    Fixture,
    GovernorMode,
    GovernorState,
    Leg,
    Quote,
    Settlement,
    Side,
    Slip,
    SlipStatus,
)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def upsert_fixtures(conn: sqlite3.Connection, fixtures: list[Fixture]) -> None:
    conn.executemany(
        """INSERT INTO fixtures (id, date, league, home, away, kickoff, status, home_goals, away_goals)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             status=excluded.status,
             home_goals=COALESCE(excluded.home_goals, fixtures.home_goals),
             away_goals=COALESCE(excluded.away_goals, fixtures.away_goals)""",
        [
            (
                f.id,
                f.date,
                f.league,
                f.home,
                f.away,
                f.kickoff,
                f.status,
                f.home_goals,
                f.away_goals,
            )
            for f in fixtures
        ],
    )
    conn.commit()


def fixtures_for_date(conn: sqlite3.Connection, day: str) -> list[Fixture]:
    rows = conn.execute("SELECT * FROM fixtures WHERE date = ? ORDER BY kickoff", (day,)).fetchall()
    return [_row_fixture(r) for r in rows]


def _row_fixture(r: sqlite3.Row) -> Fixture:
    return Fixture(
        id=r["id"],
        date=r["date"],
        league=r["league"],
        home=r["home"],
        away=r["away"],
        kickoff=r["kickoff"],
        status=r["status"],
        home_goals=r["home_goals"],
        away_goals=r["away_goals"],
    )


def save_quotes(conn: sqlite3.Connection, quotes: list[Quote]) -> None:
    conn.executemany(
        """INSERT OR REPLACE INTO snapshots
           (fixture_id, ts, bookmaker, home_o, draw_o, away_o)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [(q.fixture_id, q.ts, q.bookmaker, q.home_o, q.draw_o, q.away_o) for q in quotes],
    )
    conn.commit()


def quotes_for_date(conn: sqlite3.Connection, day: str) -> dict[int, list[Quote]]:
    rows = conn.execute(
        """SELECT s.* FROM snapshots s JOIN fixtures f ON f.id = s.fixture_id
           WHERE f.date = ?""",
        (day,),
    ).fetchall()
    out: dict[int, list[Quote]] = {}
    for r in rows:
        out.setdefault(r["fixture_id"], []).append(
            Quote(
                fixture_id=r["fixture_id"],
                bookmaker=r["bookmaker"],
                ts=r["ts"],
                home_o=r["home_o"],
                draw_o=r["draw_o"],
                away_o=r["away_o"],
            )
        )
    return out


def create_slip(conn: sqlite3.Connection, slip: Slip, mode_label: str) -> int:
    cur = conn.execute(
        """INSERT INTO slips (date, legs_json, total_odds, joint_p, eff_joint_p,
                               bonus_pct, stake, mode, status, validated)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
        (
            slip.date,
            json.dumps([l.to_json() for l in slip.legs]),
            round(slip.total_odds, 4),
            round(slip.joint_p, 6),
            round(slip.eff_joint_p, 6),
            slip.bonus_pct,
            slip.stake,
            mode_label,
            SlipStatus.PENDING.value,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def latest_pending_slip(conn: sqlite3.Connection, day: str) -> tuple[int, Slip] | None:
    row = conn.execute(
        "SELECT * FROM slips WHERE date = ? AND status = ? ORDER BY id DESC LIMIT 1",
        (day, SlipStatus.PENDING.value),
    ).fetchone()
    if row is None:
        return None
    return row["id"], _row_slip(row)


def _row_slip(r: sqlite3.Row) -> Slip:
    legs_data = json.loads(r["legs_json"])
    legs = []
    for d in legs_data:
        fx = Fixture(
            id=d["fixture_id"],
            date=d.get("kickoff", "")[:10],
            league=d["league"],
            home=d["home"],
            away=d["away"],
            kickoff=d["kickoff"],
        )
        legs.append(
            Leg(
                fixture=fx,
                side=Side(d["side"]),
                odds=d["odds"],
                model_p=d["model_p"],
                consensus_p=d["consensus_p"],
                blended_p=d["blended_p"],
                eff_p=d["eff_p"],
                eligible_2up=bool(d["eligible_2up"]),
            )
        )
    slip = Slip(date=r["date"], legs=legs)
    slip.total_odds = r["total_odds"]
    slip.joint_p = r["joint_p"]
    slip.eff_joint_p = r["eff_joint_p"]
    slip.bonus_pct = r["bonus_pct"]
    slip.stake = r["stake"]
    slip.mode = r["mode"]
    slip.status = SlipStatus(r["status"])
    return slip


def set_slip_status(
    conn: sqlite3.Connection, slip_id: int, status: SlipStatus, bet_id: str | None = None
) -> None:
    conn.execute(
        "UPDATE slips SET status = ?, bet_id = COALESCE(?, bet_id), placed_at = CASE WHEN ? = 'PLACED' THEN ? ELSE placed_at END",
        (status.value, bet_id, status.value, _now()),
    )
    conn.commit()


def save_settlement(conn: sqlite3.Connection, s: Settlement) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO settlements
           (slip_id, result, via_2up, payout, bonus_paid, settled_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (s.slip_id, s.result, int(s.via_2up), s.payout, s.bonus_paid, s.settled_at),
    )
    conn.execute("UPDATE slips SET status = ? WHERE id = ?", (SlipStatus.SETTLED.value, s.slip_id))
    conn.commit()


def ledger_record(
    conn: sqlite3.Connection,
    kind: str,
    bankroll_before: float,
    delta: float,
    ref: str | None = None,
) -> float:
    after = round(bankroll_before + delta, 2)
    conn.execute(
        """INSERT INTO ledger (ts, kind, bankroll_before, delta, bankroll_after, ref)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (_now(), kind, bankroll_before, round(delta, 2), after, ref),
    )
    meta_set(conn, "bankroll", str(after))
    conn.commit()
    return after


def meta_get(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def meta_set(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


def get_bankroll(conn: sqlite3.Connection, default: float) -> float:
    raw = meta_get(conn, "bankroll")
    return float(raw) if raw is not None else default


def load_governor(conn: sqlite3.Connection) -> GovernorState:
    raw = meta_get(conn, "governor")
    if not raw:
        return GovernorState()
    d = json.loads(raw)
    return GovernorState(
        mode=GovernorMode(d.get("mode", "PAPER_FLOOR")),
        tier_idx=int(d.get("tier_idx", 0)),
        demoted=bool(d.get("demoted", False)),
        consec_losses=int(d.get("consec_losses", 0)),
        high_watermark=float(d.get("high_watermark", 0.0)),
    )


def save_governor(conn: sqlite3.Connection, state: GovernorState) -> None:
    meta_set(
        conn,
        "governor",
        json.dumps(
            {
                "mode": state.mode.value,
                "tier_idx": state.tier_idx,
                "demoted": state.demoted,
                "consec_losses": state.consec_losses,
                "high_watermark": state.high_watermark,
            }
        ),
    )


def recent_settled(conn: sqlite3.Connection, limit: int = 60) -> list[dict]:
    rows = conn.execute(
        """SELECT s.eff_joint_p AS p, st.result AS result, st.via_2up AS via2
           FROM settlements st JOIN slips s ON s.id = st.slip_id
           ORDER BY st.settled_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [{"p": r["p"], "won": r["result"] == "WIN", "via_2up": bool(r["via2"])} for r in rows]


def consecutive_losses(conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        """SELECT st.result FROM settlements st JOIN slips s ON s.id = st.slip_id
           ORDER BY st.settled_at DESC LIMIT 50"""
    ).fetchall()
    n = 0
    for r in rows:
        if r["result"] == "LOSS":
            n += 1
        else:
            break
    return n


def brier_window(conn: sqlite3.Connection, window: int) -> tuple[float | None, int]:
    res = recent_settled(conn, window)
    if len(res) == 0:
        return None, 0
    b = sum((r["p"] - (1.0 if r["won"] else 0.0)) ** 2 for r in res) / len(res)
    return b, len(res)


def api_calls_today(conn: sqlite3.Connection, day: str) -> int:
    row = conn.execute("SELECT calls FROM api_usage WHERE day = ?", (day,)).fetchone()
    return int(row["calls"]) if row else 0


def api_call_incr(conn: sqlite3.Connection, day: str, n: int = 1) -> int:
    conn.execute(
        """INSERT INTO api_usage (day, calls) VALUES (?, ?)
           ON CONFLICT(day) DO UPDATE SET calls = calls + excluded.calls""",
        (day, n),
    )
    conn.commit()
    return api_calls_today(conn, day)


def unsettled_slips_for_date(conn: sqlite3.Connection, day: str) -> list[tuple[int, Slip]]:
    rows = conn.execute(
        "SELECT * FROM slips WHERE date = ? AND status IN (?, ?)",
        (day, SlipStatus.PLACED.value, SlipStatus.VALIDATED.value),
    ).fetchall()
    return [(r["id"], _row_slip(r)) for r in rows]


def update_fixture_result(
    conn: sqlite3.Connection,
    fixture_id: int,
    status: str,
    home_goals: int | None,
    away_goals: int | None,
) -> None:
    conn.execute(
        "UPDATE fixtures SET status = ?, home_goals = ?, away_goals = ? WHERE id = ?",
        (status, home_goals, away_goals, fixture_id),
    )
    conn.commit()
