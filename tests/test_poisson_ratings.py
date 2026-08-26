from __future__ import annotations

import math

import pytest

from sureodds.core.poisson import (
    dc_adjust,
    outcome_probs,
    pois_pmf,
    predict_match,
    score_matrix,
)
from sureodds.core.ratings import (
    HistoricalMatch,
    brier_scores,
    goal_expectations,
    league_averages,
    team_ratings,
)


def test_poisson_pmf_known_values():
    assert math.isclose(pois_pmf(1.0, 0), math.exp(-1))
    assert math.isclose(pois_pmf(2.0, 2), math.exp(-2) * 4 / 2)
    assert pois_pmf(0.0, 0) == 1.0


def test_score_matrix_sums_to_one():
    m = score_matrix(1.7, 1.1, max_goals=8)
    assert abs(sum(sum(r) for r in m) - 1.0) < 1e-6


def test_dc_adjust_renormalizes_and_boosts_draws():
    lam_h, lam_a = 1.3, 1.3
    raw = score_matrix(lam_h, lam_a)
    adj = dc_adjust(raw, lam_h, lam_a, rho=-0.05)
    assert abs(sum(sum(r) for r in adj) - 1.0) < 1e-9
    draw_raw = sum(raw[i][i] for i in range(len(raw)))
    draw_adj = sum(adj[i][i] for i in range(len(adj)))
    assert draw_adj > draw_raw


def test_outcome_monotonic_in_lambda_gap():
    _, probs = predict_match(2.2, 0.9)
    assert probs["HOME"] > probs["AWAY"]
    _, flipped = predict_match(0.9, 2.2)
    assert flipped["AWAY"] > flipped["HOME"]


def _matches():
    return [
        HistoricalMatch("2026-08-01", "A", "B", 3, 1),
        HistoricalMatch("2026-08-02", "B", "A", 0, 2),
        HistoricalMatch("2026-07-01", "A", "C", 2, 2),
        HistoricalMatch("2026-06-01", "C", "B", 1, 0),
    ]


def test_league_averages_time_weighting():
    recent_heavy = _matches()[:2]
    avg_h, avg_a = league_averages(recent_heavy, half_life_days=120)
    assert avg_h == pytest.approx(1.5, abs=0.02) and avg_a == pytest.approx(1.5, abs=0.02)

    with_old = [
        HistoricalMatch("2026-08-01", "A", "B", 2, 1),
        HistoricalMatch("2025-09-01", "C", "D", 0, 0),
    ]
    avg_h2, _ = league_averages(with_old, half_life_days=120)
    assert avg_h2 > 1.0


def test_team_ratings_shrinkage_toward_one():
    ms = [
        HistoricalMatch("2026-08-01", "A", "B", 3, 1),
        HistoricalMatch("2026-08-02", "B", "A", 1, 1),
        HistoricalMatch("2026-08-03", "A", "C", 2, 0),
    ]
    rt = team_ratings(ms, half_life_days=120, prior_matches=8)
    for team in ("A", "B"):
        for fld in ("att_h", "def_h", "att_a", "def_a"):
            assert 0.2 < getattr(rt[team], fld) < 5.0
    assert rt["A"].att_h < 2.0


def test_goal_expectations_unknown_teams_fall_back_to_average():
    rt = team_ratings(_matches(), half_life_days=120, prior_matches=8)
    avg_h, avg_a = league_averages(_matches(), half_life_days=120)
    lh, la = goal_expectations({}, "ZZZ", "YYY", avg_h, avg_a)
    assert math.isclose(lh, avg_h)
    assert math.isclose(la, avg_a)


def test_brier_score_basic():
    assert brier_scores([1, 0], [1.0, 0.0]) == 0.0
    assert math.isclose(brier_scores([1], [0.5]), 0.25)
