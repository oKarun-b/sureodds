from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime

from .models import TeamRatings


@dataclass(frozen=True)
class HistoricalMatch:
    date: str
    home: str
    away: str
    hg: int
    ag: int


def _parse_day(raw: str) -> date:
    return datetime.fromisoformat(raw[:10]).date()


def _weight(match_day: date, ref: date, half_life_days: float) -> float:
    age = max((ref - match_day).days, 0)
    return 0.5 ** (age / half_life_days)


def league_averages(
    matches: list[HistoricalMatch], half_life_days: float, ref: date | None = None
) -> tuple[float, float]:
    ref = ref or _parse_day(max(m.date for m in matches))
    sw = sh = sa = 0.0
    for m in matches:
        w = _weight(_parse_day(m.date), ref, half_life_days)
        sw += w
        sh += w * m.hg
        sa += w * m.ag
    if sw == 0:
        raise ValueError("no historical matches provided")
    return sh / sw, sa / sw


def team_ratings(
    matches: list[HistoricalMatch],
    half_life_days: float,
    prior_matches: int,
    ref: date | None = None,
) -> dict[str, TeamRatings]:
    if not matches:
        raise ValueError("no historical matches provided")
    ref = ref or _parse_day(max(m.date for m in matches))
    avg_home, avg_away = league_averages(matches, half_life_days, ref)

    acc: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    def add(team: str, key: str, val: float) -> None:
        acc[team][key] += val

    for m in matches:
        w = _weight(_parse_day(m.date), ref, half_life_days)
        add(m.home, "hs", w * m.hg)
        add(m.home, "hc", w * m.ag)
        add(m.home, "nh", w)
        add(m.away, "as_", w * m.ag)
        add(m.away, "ac", w * m.hg)
        add(m.away, "na", w)

    out: dict[str, TeamRatings] = {}
    eps = 1e-9
    avg_home_safe = avg_home if abs(avg_home) > eps else eps
    avg_away_safe = avg_away if abs(avg_away) > eps else eps
    for team, a in acc.items():
        nh, na = a["nh"], a["na"]
        att_h_raw = (a["hs"] / nh) / avg_home_safe if nh > 0 else 1.0
        def_h_raw = (a["hc"] / nh) / avg_away_safe if nh > 0 else 1.0
        att_a_raw = (a["as_"] / na) / avg_away_safe if na > 0 else 1.0
        def_a_raw = (a["ac"] / na) / avg_home_safe if na > 0 else 1.0
        k = float(prior_matches)
        out[team] = TeamRatings(
            att_h=(nh * att_h_raw + k) / (nh + k),
            def_h=(nh * def_h_raw + k) / (nh + k),
            att_a=(na * att_a_raw + k) / (na + k),
            def_a=(na * def_a_raw + k) / (na + k),
            n_home=nh,
            n_away=na,
        )
    return out


def goal_expectations(
    ratings: dict[str, TeamRatings],
    home_team: str,
    away_team: str,
    avg_home: float,
    avg_away: float,
) -> tuple[float, float]:
    rh = ratings.get(home_team)
    ra = ratings.get(away_team)
    att_h = rh.att_h if rh else 1.0
    def_a = ra.def_a if ra else 1.0
    att_a = ra.att_a if ra else 1.0
    def_h = rh.def_h if rh else 1.0
    lam_h = max(min(att_h * def_a * avg_home, 5.0), 0.05)
    lam_a = max(min(att_a * def_h * avg_away, 5.0), 0.05)
    return lam_h, lam_a


def brier_scores(y_true: list[int], y_prob: list[float]) -> float:
    if not y_true:
        raise ValueError("empty sample")
    return sum((p - t) ** 2 for t, p in zip(y_true, y_prob)) / len(y_true)


def safe_log(x: float) -> float:
    return math.log(x) if x > 0 else float("-inf")
