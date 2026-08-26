from __future__ import annotations

import pytest
from types import SimpleNamespace

from sureodds.core.models import GovernorMode, GovernorState
from sureodds.core.staking import decide_stake, kelly_fraction, update_after_result

MIN_STAKE = 50.0


def _cfg():
    growth = SimpleNamespace(
        active_below_bankroll=100_000,
        cap_pct=0.20,
        demote_pct=0.05,
        max_consecutive_losses=2,
        max_drawdown=0.40,
    )
    security = SimpleNamespace(
        tiers=[0.125, 0.25, 0.5],
        window_slips=60,
        promote_brier_tier2=0.240,
        promote_brier_tier3=0.225,
        demote_brier=0.260,
    )
    return SimpleNamespace(staking=SimpleNamespace(min_stake=MIN_STAKE, paper_floor_bankroll=10_000, growth=growth, security=security))


def test_kelly_zero_when_no_edge():
    assert kelly_fraction(0.45, 2.0) == 0.0
    assert kelly_fraction(0.55, 2.0) == pytest.approx(0.10)


def test_paper_floor_below_threshold_bankroll():
    d = decide_stake(GovernorState(), 1_000, 0.60, 2.0, _cfg())
    assert d.stake == MIN_STAKE
    assert d.state.mode == GovernorMode.PAPER_FLOOR


def test_growth_mode_caps_at_twenty_percent():
    d = decide_stake(GovernorState(), 50_000, 0.60, 2.0, _cfg())
    assert d.state.mode == GovernorMode.GROWTH
    assert d.stake == 10_000.00


def test_growth_mode_demoted_uses_five_percent():
    s = GovernorState(mode=GovernorMode.GROWTH, demoted=True)
    d = decide_stake(s, 50_000, 0.60, 2.0, _cfg())
    assert d.stake == 2_500.00


def test_security_mode_applies_tiered_kelly():
    d = decide_stake(GovernorState(), 1_000_000, 0.55, 2.0, _cfg(), brier=None, window_n=0)
    assert d.state.mode == GovernorMode.SECURITY
    expected = min(1_000_000 * 0.10 * 0.125, 1_000_000 * 0.10)
    assert d.stake == round(expected, 2)


def test_security_promotion_via_brier():
    good = decide_stake(GovernorState(), 1_000_000, 0.55, 2.0, _cfg(), brier=0.220, window_n=60)
    assert good.state.tier_idx == 2
    mid = decide_stake(GovernorState(), 1_000_000, 0.55, 2.0, _cfg(), brier=0.235, window_n=60)
    assert mid.state.tier_idx == 1
    bad = decide_stake(GovernorState(tier_idx=1), 1_000_000, 0.55, 2.0, _cfg(), brier=0.275, window_n=60)
    assert bad.state.tier_idx == 0
    short_window = decide_stake(GovernorState(), 1_000_000, 0.55, 2.0, _cfg(), brier=0.100, window_n=10)
    assert short_window.state.tier_idx == 0


def test_two_consecutive_losses_demote_growth_mode():
    cfg = _cfg()
    s = GovernorState(mode=GovernorMode.GROWTH, high_watermark=50_000)
    s = update_after_result(s, won=False, bankroll_now=47_500, cfg=cfg)
    s = update_after_result(s, won=False, bankroll_now=46_000, cfg=cfg)
    assert s.demoted is True
    assert s.consec_losses == 2


def test_drawdown_triggers_demote():
    cfg = _cfg()
    s = GovernorState(mode=GovernorMode.GROWTH, high_watermark=50_000)
    s = update_after_result(s, won=False, bankroll_now=28_000, cfg=cfg)
    assert s.demoted is True


def test_recovery_clears_demotion():
    cfg = _cfg()
    s = GovernorState(mode=GovernorMode.GROWTH, high_watermark=50_000, demoted=True)
    s = update_after_result(s, won=True, bankroll_now=49_500, cfg=cfg)
    assert s.demoted is False
    assert s.consec_losses == 0
