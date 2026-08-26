from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class TargetCfg:
    odds_low: float
    odds_high: float


@dataclass(frozen=True)
class LegsCfg:
    min: int
    max: int
    odds_min: float
    odds_max: float


@dataclass(frozen=True)
class FiltersCfg:
    min_bookmakers: int
    model_min_prob: float
    consensus_min_prob: float


@dataclass(frozen=True)
class BlendCfg:
    w_model: float


@dataclass(frozen=True)
class RatingsCfg:
    half_life_days: int
    prior_matches: int
    max_goals: int


@dataclass(frozen=True)
class WinBonusCfg:
    min_leg_odds: float
    pct_by_legs: dict[int, float]


@dataclass(frozen=True)
class GrowthCfg:
    active_below_bankroll: float
    cap_pct: float
    demote_pct: float
    max_consecutive_losses: int
    max_drawdown: float


@dataclass(frozen=True)
class SecurityCfg:
    tiers: list[float]
    window_slips: int
    promote_brier_tier2: float
    promote_brier_tier3: float
    demote_brier: float


@dataclass(frozen=True)
class StakingCfg:
    min_stake: float
    paper_floor_bankroll: float
    growth: GrowthCfg
    security: SecurityCfg


@dataclass(frozen=True)
class ScheduleCfg:
    pick: str
    settle: str


@dataclass(frozen=True)
class ApiCfg:
    football_base: str
    daily_call_budget: int


@dataclass(frozen=True)
class AppConfig:
    timezone: str
    currency: str
    target: TargetCfg
    legs: LegsCfg
    filters: FiltersCfg
    blend: BlendCfg
    ratings: RatingsCfg
    win_bonus: WinBonusCfg
    staking: StakingCfg
    schedule: ScheduleCfg
    api: ApiCfg
    db_path: Path
    env: dict[str, str] = field(default_factory=dict)


def _build(d: dict, env: dict[str, str]) -> AppConfig:
    return AppConfig(
        timezone=d["timezone"],
        currency=d["currency"],
        target=TargetCfg(**d["target"]),
        legs=LegsCfg(**d["legs"]),
        filters=FiltersCfg(**d["filters"]),
        blend=BlendCfg(**d["blend"]),
        ratings=RatingsCfg(**d["ratings"]),
        win_bonus=WinBonusCfg(
            min_leg_odds=d["win_bonus"]["min_leg_odds"],
            pct_by_legs={int(k): float(v) for k, v in d["win_bonus"]["pct_by_legs"].items()},
        ),
        staking=StakingCfg(
            min_stake=d["staking"]["min_stake"],
            paper_floor_bankroll=d["staking"]["paper_floor_bankroll"],
            growth=GrowthCfg(**d["staking"]["growth"]),
            security=SecurityCfg(**d["staking"]["security"]),
        ),
        schedule=ScheduleCfg(**d["schedule"]),
        api=ApiCfg(**d["api"]),
        db_path=Path(env.get("SUREODDS_DB", "data/sureodds.db")),
        env=env,
    )


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    with open(path, encoding="utf-8") as fh:
        d = yaml.safe_load(fh)
    env = {
        k: v
        for k, v in os.environ.items()
        if k.startswith(("API_", "TELEGRAM_", "BETPAWA_", "SUREODDS_"))
    }
    return _build(d, env)


def apply_dotenv(path: str | Path = ".env") -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(path)
    except ImportError:
        pass
