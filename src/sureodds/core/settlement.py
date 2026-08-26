from __future__ import annotations

from dataclasses import dataclass

from .models import Side


@dataclass(frozen=True)
class LegResult:
    outcome: str
    via_2up: bool


def leg_outcome(home_goals: int, away_goals: int, side: Side, ever2up_side: bool) -> LegResult:
    if side == Side.HOME:
        board_win = home_goals > away_goals
    elif side == Side.AWAY:
        board_win = away_goals > home_goals
    else:
        board_win = home_goals == away_goals

    if board_win:
        return LegResult("WIN", False)
    if side != Side.DRAW and ever2up_side:
        return LegResult("WIN", True)
    return LegResult("LOSS", False)


def settle(
    results: list[LegResult],
    stake: float,
    total_odds: float,
    bonus_pct: float,
) -> tuple[str, float, float, bool]:
    if not results:
        raise ValueError("no leg results")
    all_win = all(r.outcome == "WIN" for r in results)
    via_2up = any(r.via_2up for r in results)
    if not all_win:
        return "LOSS", 0.0, 0.0, via_2up
    payout = stake * total_odds * (1.0 + bonus_pct)
    bonus = stake * total_odds * bonus_pct
    return "WIN", round(payout, 2), round(bonus, 2), via_2up
