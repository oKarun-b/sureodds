from __future__ import annotations

import copy
from datetime import UTC, datetime

from ..config import AppConfig
from .models import GovernorMode, GovernorState, StakeDecision


def kelly_fraction(p: float, odds: float) -> float:
    if odds <= 1.0 or p <= 0.0:
        return 0.0
    f = (p * odds - 1.0) / (odds - 1.0)
    return max(f, 0.0)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def decide_stake(
    state: GovernorState,
    bankroll: float,
    p: float,
    odds: float,
    cfg: AppConfig,
    brier: float | None = None,
    window_n: int = 0,
) -> StakeDecision:
    scfg = cfg.staking
    new_state = copy.deepcopy(state)
    new_state.high_watermark = max(state.high_watermark, bankroll)
    new_state.mode = state.mode

    if bankroll < scfg.paper_floor_bankroll:
        new_state.mode = GovernorMode.PAPER_FLOOR
        return StakeDecision(scfg.min_stake, new_state, "paper floor: flat min stake")

    if bankroll < scfg.growth.active_below_bankroll:
        new_state.mode = GovernorMode.GROWTH
        pct = scfg.growth.demote_pct if state.demoted else scfg.growth.cap_pct
        reason = "growth mode (demoted)" if state.demoted else "growth mode"
        stake = min(bankroll * pct, bankroll)
        stake = max(stake, min(scfg.min_stake, bankroll))
        return StakeDecision(round(stake, 2), new_state, reason)

    new_state.mode = GovernorMode.SECURITY
    tiers = scfg.security.tiers
    tier_idx = state.tier_idx

    if brier is not None and window_n >= scfg.security.window_slips:
        while tier_idx < len(tiers) - 1 and _can_promote(tier_idx, brier, scfg.security):
            tier_idx += 1
        if brier > scfg.security.demote_brier:
            tier_idx = 0
    new_state.tier_idx = tier_idx

    full = kelly_fraction(p, odds)
    frac = full * tiers[tier_idx]
    hard_cap = 0.10
    stake = min(bankroll * frac, bankroll * hard_cap)
    stake = max(stake, min(scfg.min_stake, bankroll))
    label = f"security tier {tier_idx + 1} ({tiers[tier_idx]:.3f} x kelly)"
    return StakeDecision(round(stake, 2), new_state, label)


def _can_promote(tier_idx: int, brier: float, scfg) -> bool:
    if tier_idx == 0:
        return brier <= scfg.promote_brier_tier2
    if tier_idx == 1:
        return brier <= scfg.promote_brier_tier3
    return False


def update_after_result(
    state: GovernorState,
    won: bool,
    bankroll_now: float,
    cfg: AppConfig,
) -> GovernorState:
    g = cfg.staking.growth
    ns = copy.deepcopy(state)

    if won:
        ns.consec_losses = 0
    else:
        ns.consec_losses += 1
        if ns.consec_losses >= g.max_consecutive_losses and ns.mode == GovernorMode.GROWTH:
            ns.demoted = True

    ns.high_watermark = max(ns.high_watermark, bankroll_now)
    if ns.high_watermark > 0:
        dd = (ns.high_watermark - bankroll_now) / ns.high_watermark
        if dd >= g.max_drawdown and ns.mode == GovernorMode.GROWTH:
            ns.demoted = True

    if ns.demoted and bankroll_now >= ns.high_watermark * 0.98:
        ns.demoted = False

    return ns
