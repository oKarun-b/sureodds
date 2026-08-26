from __future__ import annotations

from dataclasses import dataclass

from ..config import AppConfig
from .models import Fixture, Leg, Quote, Side
from .poisson import predict_match
from .ratings import goal_expectations
from .two_up import p_ever_two_up

_SIDE_KEYS = {Side.HOME: "home_o", Side.DRAW: "draw_o", Side.AWAY: "away_o"}


def devig(h: float, d: float, a: float) -> tuple[float, float, float]:
    ih, id_, ia = 1.0 / h, 1.0 / d, 1.0 / a
    total = ih + id_ + ia
    if total <= 0:
        raise ValueError("non-positive book")
    return ih / total, id_ / total, ia / total


@dataclass(frozen=True)
class Consensus:
    probs: dict[Side, float]
    best_odds: dict[Side, float]
    n_books: int


def consensus(quotes: list[Quote]) -> Consensus | None:
    latest_by_book: dict[str, Quote] = {}
    for q in quotes:
        cur = latest_by_book.get(q.bookmaker)
        if cur is None or q.ts > cur.ts:
            latest_by_book[q.bookmaker] = q
    qs = list(latest_by_book.values())
    if not qs:
        return None

    sums = {s: 0.0 for s in Side}
    best = {s: 0.0 for s in Side}
    for q in qs:
        dh, dd, da = devig(q.home_o, q.draw_o, q.away_o)
        vals = {Side.HOME: dh, Side.DRAW: dd, Side.AWAY: da}
        for s in Side:
            sums[s] += vals[s]
            best[s] = max(best[s], getattr(q, _SIDE_KEYS[s]))
    n = len(qs)
    return Consensus(
        probs={s: sums[s] / n for s in Side},
        best_odds=best,
        n_books=n,
    )


def evaluate_candidates(
    fixtures: list[Fixture],
    quotes_by_fixture: dict[int, list[Quote]],
    ratings: dict,
    avg_home: float,
    avg_away: float,
    cfg: AppConfig,
    eligible_2up: set[int] | None = None,
    rho: float = -0.05,
) -> list[Leg]:
    eligible_2up = eligible_2up or set()
    out: list[Leg] = []
    w = cfg.blend.w_model
    mg = cfg.ratings.max_goals

    for fx in fixtures:
        quotes = quotes_by_fixture.get(fx.id)
        if not quotes:
            continue
        cons = consensus(quotes)
        if cons is None or cons.n_books < cfg.filters.min_bookmakers:
            continue

        lam_h, lam_a = goal_expectations(ratings, fx.home, fx.away, avg_home, avg_away)
        _, probs = predict_match(lam_h, lam_a, rho=rho, max_goals=mg)
        tu = p_ever_two_up(lam_h, lam_a, max_goals=mg) if fx.id in eligible_2up else None

        for side in Side:
            odds = cons.best_odds[side]
            if not (cfg.legs.odds_min <= odds <= cfg.legs.odds_max):
                continue
            model_p = probs[side.value]
            cons_p = cons.probs[side]
            if model_p < cfg.filters.model_min_prob:
                continue
            if cons_p < cfg.filters.consensus_min_prob:
                continue
            blended = w * model_p + (1.0 - w) * cons_p
            is_2up = tu is not None and side != Side.DRAW
            eff = tu[side.value] if is_2up else blended
            out.append(
                Leg(
                    fixture=fx,
                    side=side,
                    odds=odds,
                    model_p=model_p,
                    consensus_p=cons_p,
                    blended_p=blended,
                    eff_p=eff,
                    eligible_2up=is_2up,
                    ever2up_p=tu[side.value] if tu else None,
                )
            )
    out.sort(key=lambda l: l.eff_p, reverse=True)
    return out
