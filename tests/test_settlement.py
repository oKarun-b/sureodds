from __future__ import annotations

import pytest

from sureodds.core.models import Side
from sureodds.core.settlement import leg_outcome, settle


def test_board_win_is_plain_win():
    r = leg_outcome(2, 0, Side.HOME, ever2up_side=True)
    assert r.outcome == "WIN" and r.via_2up is False


def test_board_loss_rescued_by_two_up():
    r = leg_outcome(1, 2, Side.HOME, ever2up_side=True)
    assert r.outcome == "WIN" and r.via_2up is True


def test_board_loss_without_two_up_is_loss():
    r = leg_outcome(0, 1, Side.HOME, ever2up_side=False)
    assert r.outcome == "LOSS" and r.via_2up is False


def test_draw_never_qualifies_for_two_up():
    r = leg_outcome(2, 2, Side.DRAW, ever2up_side=True)
    assert r.outcome == "WIN"
    r2 = leg_outcome(1, 2, Side.DRAW, ever2up_side=True)
    assert r2.outcome == "LOSS" and r2.via_2up is False


def test_settle_winning_multibet_with_bonus():
    results = [leg_outcome(2, 0, Side.HOME, False), leg_outcome(1, 2, Side.HOME, True)]
    result, payout, bonus, via = settle(results, stake=100.0, total_odds=2.0, bonus_pct=0.03)
    assert result == "WIN"
    assert payout == pytest.approx(206.0)
    assert bonus == pytest.approx(6.0)
    assert via is True


def test_settle_loss_has_zero_payout_but_keeps_flag():
    rescued = leg_outcome(1, 2, Side.HOME, ever2up_side=True)
    pure_loss = leg_outcome(3, 0, Side.AWAY, ever2up_side=False)
    results = [rescued, pure_loss]
    result, payout, bonus, via = settle(results, stake=100.0, total_odds=2.0, bonus_pct=0.03)
    assert result == "LOSS"
    assert payout == 0.0
    assert bonus == 0.0
    assert via is True


def test_settle_requires_results():
    with pytest.raises(ValueError):
        settle([], 10.0, 2.0, 0.0)
