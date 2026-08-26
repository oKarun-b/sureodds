from __future__ import annotations

from itertools import combinations

from ..config import AppConfig
from .models import Leg, Slip


def _bonus(cfg: AppConfig, n_legs: int) -> float:
    return cfg.win_bonus.pct_by_legs.get(n_legs, 0.0)


def build_slip(candidates: list[Leg], cfg: AppConfig, date: str) -> Slip | None:
    lo, hi = cfg.target.odds_low, cfg.target.odds_high
    pool = sorted(candidates, key=lambda l: (l.eff_p, l.odds), reverse=True)[:60]

    best: tuple[float, float, tuple[Leg, ...]] | None = None

    for size in range(cfg.legs.min, cfg.legs.max + 1):
        bonus = _bonus(cfg, size)

        def consider(combo: tuple[Leg, ...], bonus=bonus) -> None:
            nonlocal best
            total = 1.0
            joint = 1.0
            for leg in combo:
                total *= leg.odds
                joint *= leg.eff_p
            if not (lo <= total <= hi):
                return
            key = (joint * (1.0 + bonus), total)
            if best is None or key > (best[0], best[1]):
                best = (key[0], key[1], combo)

        for combo in combinations(pool, size):
            fixtures = {c.fixture.id for c in combo}
            if len(fixtures) != size:
                continue
            prod_odds = 1.0
            early_ok = True
            for c in combo:
                prod_odds *= c.odds
                if prod_odds > hi:
                    early_ok = False
                    break
            if not early_ok:
                continue
            consider(combo)

    if best is None:
        return None

    legs = list(best[2])
    slip = Slip(date=date, legs=legs)
    slip.total_odds = 1.0
    slip.joint_p = 1.0
    slip.eff_joint_p = 1.0
    for leg in legs:
        slip.total_odds *= leg.odds
        slip.joint_p *= leg.blended_p
        slip.eff_joint_p *= leg.eff_p
    slip.bonus_pct = _bonus(cfg, len(legs))
    return slip
