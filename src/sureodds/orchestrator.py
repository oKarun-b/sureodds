from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from .config import AppConfig
from .core import accumulator, blend, settlement, staking
from .core.models import Fixture, Settlement, Side
from .core.ratings import HistoricalMatch, league_averages, team_ratings
from .providers.api_football import ApiFootball
from .storage import repo


def today(cfg: AppConfig) -> str:
    return datetime.now(ZoneInfo(cfg.timezone)).date().isoformat()


def days_ago(cfg: AppConfig, n: int) -> str:
    return (datetime.now(ZoneInfo(cfg.timezone)).date() - timedelta(days=n)).isoformat()


def make_provider(cfg: AppConfig, conn) -> ApiFootball:
    day = today(cfg)
    counter = lambda: repo.api_calls_today(conn, day)
    return ApiFootball(
        api_key=cfg.env.get("API_FOOTBALL_KEY", ""),
        base_url=cfg.api.football_base,
        call_counter=counter,
        daily_budget=cfg.api.daily_call_budget,
    )


def window_for_day(cfg: AppConfig, day: str) -> tuple[datetime, datetime]:
    start = datetime.fromisoformat(day).replace(tzinfo=ZoneInfo(cfg.timezone)).replace(hour=9, minute=0, second=0)
    end = start + timedelta(days=1)
    return start.astimezone(UTC), end.astimezone(UTC)


def fetch(cfg: AppConfig, conn, day: str | None = None) -> dict:
    day = day or today(cfg)
    prov = make_provider(cfg, conn)
    start, end = window_for_day(cfg, day)
    start_day = start.astimezone(ZoneInfo(cfg.timezone)).date().isoformat()
    end_day = end.astimezone(ZoneInfo(cfg.timezone)).date().isoformat()
    days = {start_day, end_day}
    all_fixtures: list = []
    all_quotes: list = []
    for d in sorted(days):
        try:
            fxs = prov.get_fixtures(d)
        except RuntimeError as e:
            if "Free plans do not have access to this date" in str(e):
                print(f"skip {d}: free plan window limit")
                continue
            raise
        all_fixtures.extend(fxs)
        repo.upsert_fixtures(conn, fxs)
        try:
            odds = prov.get_odds(d)
        except RuntimeError as e:
            if "Free plans do not have access to this date" in str(e) or "Page parameter" in str(e):
                print(f"skip odds for {d}: {e}")
                continue
            raise
        qs = [q for lst in odds.values() for q in lst]
        all_quotes.extend(qs)
        repo.save_quotes(conn, qs)
    return {"day": day, "window": f"{start.isoformat()} -> {end.isoformat()}", "fixtures": len(all_fixtures), "quote_rows": len(all_quotes)}


def historical_matches(conn, limit: int = 1500) -> list[HistoricalMatch]:
    rows = conn.execute(
        """SELECT date, home, away, home_goals, away_goals FROM fixtures
           WHERE status = 'FT' AND home_goals IS NOT NULL AND away_goals IS NOT NULL
           ORDER BY date DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [
        HistoricalMatch(r["date"], r["home"], r["away"], int(r["home_goals"]), int(r["away_goals"]))
        for r in rows
    ]


def _rating_context(conn, cfg: AppConfig):
    hist = historical_matches(conn)
    if len(hist) < 30:
        return 1.40, 1.15, {}
    avg_h, avg_a = league_averages(hist, cfg.ratings.half_life_days)
    rt = team_ratings(hist, cfg.ratings.half_life_days, cfg.ratings.prior_matches)
    return avg_h, avg_a, rt


def format_card(slip_id: int, slip, reason: str) -> str:
    lines = [
        f"SUREODDS SLIP #{slip_id} -- {slip.date}",
        f"Mode: {slip.mode or 'PENDING'} | Stake: {slip.stake:.0f} FCFA",
        "",
    ]
    for leg in slip.legs:
        tag = " [2UP]" if leg.eligible_2up else ""
        pick = leg.fixture.home if leg.side.value == "HOME" else leg.fixture.away
        lines.append(f"- {leg.fixture.home} vs {leg.fixture.away} -- {pick}{tag} @ {leg.odds}")
        lines.append(f"   {leg.fixture.league} | ko {leg.fixture.kickoff[:16]}")
        lines.append(
            f"   model {leg.model_p:.0%} | market {leg.consensus_p:.0%} | eff {leg.eff_p:.0%}"
        )
    lines += [
        "",
        f"Total odds: {slip.total_odds:.2f} (+{slip.bonus_pct:.0%} bonus -> {slip.eff_total_odds:.2f})",
        f"Joint probability: {slip.eff_joint_p:.1%} | EV: {slip.ev:+.1%}",
        f"Engine note: {reason}",
    ]
    return "\n".join(lines)


def _fixture_in_window(fx: Fixture, start: datetime, end: datetime) -> bool:
    try:
        ko = datetime.fromisoformat(fx.kickoff.replace("Z", "+00:00"))  # noqa: FURB162
        if ko.tzinfo is None:
            ko = ko.replace(tzinfo=UTC)
        return start <= ko < end
    except (ValueError, TypeError):
        return fx.date in (start.date().isoformat(), end.date().isoformat())


def pick(
    cfg: AppConfig,
    conn,
    day: str | None = None,
    eligible_2up: set[int] | None = None,
) -> tuple[dict | None, str | None]:
    day = day or today(cfg)
    start, end = window_for_day(cfg, day)
    all_fixtures: list = []
    for d in {start.astimezone(ZoneInfo(cfg.timezone)).date().isoformat(), end.astimezone(ZoneInfo(cfg.timezone)).date().isoformat()}:
        all_fixtures.extend(repo.fixtures_for_date(conn, d))
    fixtures = [fx for fx in all_fixtures if _fixture_in_window(fx, start, end)]
    if not fixtures:
        return None, f"no fixtures in 09:00-09:00 window {start.date().isoformat()} for {cfg.timezone}; run `fetch` first"
    by_id = {fx.id: fx for fx in fixtures}
    raw_quotes: dict[int, list] = {}
    for d in {start.astimezone(ZoneInfo(cfg.timezone)).date().isoformat(), end.astimezone(ZoneInfo(cfg.timezone)).date().isoformat()}:
        qd = repo.quotes_for_date(conn, d)
        for fid, qs in qd.items():
            if fid in by_id:
                raw_quotes.setdefault(fid, []).extend(qs)
    quotes = raw_quotes

    avg_h, avg_a, rt = _rating_context(conn, cfg)
    candidates = blend.evaluate_candidates(
        fixtures, quotes, rt, avg_h, avg_a, cfg, eligible_2up=eligible_2up
    )
    slip = accumulator.build_slip(candidates, cfg, day)
    if slip is None:
        return None, (
            f"no qualifying accumulator from {len(candidates)} candidates "
            "(band/filters unsatisfied today)"
        )

    bankroll = repo.get_bankroll(conn, float(cfg.staking.paper_floor_bankroll))
    state = repo.load_governor(conn)
    brier, n_window = repo.brier_window(conn, cfg.staking.security.window_slips)
    decision = staking.decide_stake(
        state, bankroll, slip.eff_joint_p, slip.total_odds, cfg, brier=brier, window_n=n_window
    )
    slip.stake = decision.stake
    slip.mode = decision.state.mode.value

    slip_id = repo.create_slip(conn, slip, decision.state.mode.value)
    repo.save_governor(conn, decision.state)
    card = format_card(slip_id, slip, decision.reason)
    return {"slip_id": slip_id, "slip": slip, "card": card}, None


def validate_slip(conn, slip_id: int, accept: bool) -> str:
    from .core.models import SlipStatus

    row = conn.execute("SELECT status FROM slips WHERE id=?", (slip_id,)).fetchone()
    if row and row["status"] not in (SlipStatus.PENDING.value,):
        return row["status"]
    status = SlipStatus.VALIDATED if accept else SlipStatus.REJECTED
    repo.set_slip_status(conn, slip_id, status)
    return status.value


def settle(cfg: AppConfig, conn, day: str | None = None) -> list[dict]:
    day = day or days_ago(cfg, 1)
    prov = make_provider(cfg, conn)
    state = repo.load_governor(conn)
    summary = []

    for slip_id, slip in repo.unsettled_slips_for_date(conn, day):
        leg_results = []
        for leg in slip.legs:
            fxr = prov.get_result(leg.fixture.id)
            repo.update_fixture_result(conn, fxr.id, fxr.status, fxr.home_goals, fxr.away_goals)
            try:
                timeline = prov.get_goal_timeline(leg.fixture.id)
                flags = ApiFootball.two_up_flags(timeline)
            except (RuntimeError, ValueError, OSError):
                flags = {"HOME": False, "AWAY": False}
            side_flag = bool(flags.get(leg.side.value)) if leg.side != Side.DRAW else False
            lr = settlement.leg_outcome(
                fxr.home_goals or 0, fxr.away_goals or 0, leg.side, side_flag
            )
            leg_results.append(lr)

        result, payout, bonus, via_2up = settlement.settle(
            leg_results, slip.stake, slip.total_odds, slip.bonus_pct
        )
        delta = payout - slip.stake
        before = repo.get_bankroll(conn, float(cfg.staking.paper_floor_bankroll))
        after = repo.ledger_record(conn, "bet_settlement", before, delta, ref=str(slip_id))
        repo.save_settlement(
            conn,
            Settlement(
                slip_id,
                result,
                via_2up,
                payout,
                bonus,
                datetime.now(UTC).isoformat(timespec="seconds"),
            ),
        )
        new_state = staking.update_after_result(
            state, won=(result == "WIN"), bankroll_now=after, cfg=cfg
        )
        repo.save_governor(conn, new_state)
        state = new_state
        summary.append(
            {
                "slip_id": slip_id,
                "result": result,
                "via_2up": via_2up,
                "payout": payout,
                "bonus": bonus,
                "bankroll": after,
            }
        )
    return summary


def report(cfg: AppConfig, conn, window: int = 60) -> dict:
    res = repo.recent_settled(conn, window)
    n = len(res)
    wins = sum(1 for r in res if r["won"])
    rows = conn.execute(
        """SELECT s.stake AS stake, s.bonus_pct AS bonus, s.total_odds AS odds,
                  x.payout AS payout
           FROM settlements x JOIN slips s ON s.id = x.slip_id
           ORDER BY x.settled_at DESC LIMIT ?""",
        (window,),
    ).fetchall()
    staked = sum(r["stake"] for r in rows)
    returned = sum(r["payout"] for r in rows)
    brier, bwin_n = repo.brier_window(conn, cfg.staking.security.window_slips)
    state = repo.load_governor(conn)
    return {
        "settled_slips": n,
        "wins": wins,
        "win_rate": (wins / n) if n else 0.0,
        "staked": round(staked, 2),
        "returned": round(returned, 2),
        "roi": ((returned - staked) / staked) if staked else 0.0,
        "brier_window": brier,
        "brier_n": bwin_n,
        "mode": state.mode.value,
        "tier_idx": state.tier_idx,
        "demoted": state.demoted,
        "bankroll": repo.get_bankroll(conn, float(cfg.staking.paper_floor_bankroll)),
    }
