from __future__ import annotations

from sureodds.core.two_up import p_ever_two_up


def test_symmetric_low_lambdas_small_and_equal():
    out = p_ever_two_up(0.5, 0.5)
    assert abs(out["HOME"] - out["AWAY"]) < 1e-9
    assert 0.0 <= out["HOME"] < 0.15
    assert 0.0 <= out["AWAY"] < 0.15


def test_zero_lambdas_zero_probability():
    out = p_ever_two_up(0.05, 0.05)
    assert out["HOME"] >= 0.0
    assert p_ever_two_up(0.0, 0.0)["HOME"] == 0.0


def test_strong_favorite_has_meaningful_two_up_probability():
    from sureodds.core.poisson import predict_match

    lam_h, lam_a = 2.6, 0.8
    _, probs = predict_match(lam_h, lam_a, max_goals=8)
    tu = p_ever_two_up(lam_h, lam_a, max_goals=8)
    assert 0.40 < tu["HOME"] < 0.90
    assert 0.0 < tu["HOME"] < 1.0
    assert tu["AWAY"] < 0.35
    assert probs["HOME"] > 0.60


def test_monotonic_in_goal_expectation():
    low = p_ever_two_up(1.8, 1.0)["HOME"]
    high = p_ever_two_up(2.9, 1.0)["HOME"]
    assert high > low


def test_probabilities_bounded():
    out = p_ever_two_up(3.5, 2.5)
    assert 0.0 <= out["HOME"] <= 1.0
    assert 0.0 <= out["AWAY"] <= 1.0
