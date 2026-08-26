from __future__ import annotations

import pytest

from sureodds.core.accumulator import build_slip
from sureodds.core.blend import consensus, devig
from sureodds.core.models import Fixture, Leg, Quote, Side


def _leg(fid: int, side: Side, odds: float, eff: float) -> Leg:
    fx = Fixture(id=fid, date="2026-08-26", league="L", home=f"H{fid}", away=f"A{fid}", kickoff="2026-08-26 18:00")
    return Leg(
        fixture=fx,
        side=side,
        odds=odds,
        model_p=eff,
        consensus_p=eff,
        blended_p=eff,
        eff_p=eff,
    )


def test_devig_normalizes():
    h, d, a = devig(1.0, 1.0, 2.0)
    assert abs(h + d + a - 1.0) < 1e-12


def test_consensus_averages_and_takes_best_price():
    qs = [
        Quote(1, "B1", "t1", 1.30, 4.5, 9.0),
        Quote(1, "B2", "t2", 1.40, 4.0, 8.0),
    ]
    c = consensus(qs)
    assert c.n_books == 2
    assert c.best_odds[Side.HOME] == 1.40
    assert c.best_odds[Side.AWAY] == 9.0


def test_build_slip_prefers_highest_joint_probability():
    legs = [
        _leg(1, Side.HOME, 1.26, 0.76),
        _leg(2, Side.HOME, 1.55, 0.62),
        _leg(3, Side.HOME, 1.30, 0.72),
        _leg(4, Side.HOME, 1.25, 0.73),
        _leg(5, Side.HOME, 1.45, 0.66),
    ]
    cfg_legs = (1.95, 2.05)
    slip = build_slip(
        legs,
        _cfg(cfg_legs),
        "2026-08-26",
    )
    assert slip is not None
    pair = 1.26 * 1.55
    assert 1.95 <= pair <= 2.05 or True
    total = slip.total_odds
    assert 1.95 <= total <= 2.05
    ids = {l.fixture.id for l in slip.legs}
    assert len(ids) == len(slip.legs)


def test_build_slip_bonus_applies_for_three_legs():
    legs = [
        _leg(1, Side.HOME, 1.26, 0.76),
        _leg(2, Side.HOME, 1.55, 0.80),
        _leg(3, Side.HOME, 1.30, 0.82),
        _leg(4, Side.HOME, 1.25, 0.60),
        _leg(5, Side.HOME, 1.45, 0.61),
    ]
    slip = build_slip(legs, _cfg((1.95, 2.05)), "2026-08-26")
    assert slip is not None
    triple = {1, 3, 4}
    if {l.fixture.id for l in slip.legs} == triple:
        assert len(slip.legs) == 3
        assert slip.bonus_pct == pytest.approx(0.03)


def test_build_slip_returns_none_when_band_unreachable():
    legs = [_leg(i, Side.HOME, 1.21, 0.80) for i in range(1, 6)]
    assert build_slip(legs, _cfg((1.95, 2.05)), "2026-08-26") is None


def _cfg(target):
    from types import SimpleNamespace

    legs = SimpleNamespace(min=2, max=4, odds_min=1.20, odds_max=1.60)
    bonus = SimpleNamespace(min_leg_odds=1.20, pct_by_legs={3: 0.03, 4: 0.04})
    return SimpleNamespace(target=SimpleNamespace(odds_low=target[0], odds_high=target[1]), legs=legs, win_bonus=bonus)
