from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Side(str, Enum):
    HOME = "HOME"
    DRAW = "DRAW"
    AWAY = "AWAY"


class SlipStatus(str, Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    PLACED = "PLACED"
    SETTLED = "SETTLED"


class GovernorMode(str, Enum):
    PAPER_FLOOR = "PAPER_FLOOR"
    GROWTH = "GROWTH"
    SECURITY = "SECURITY"


@dataclass(frozen=True)
class Fixture:
    id: int
    date: str
    league: str
    home: str
    away: str
    kickoff: str
    status: str = "NS"
    home_goals: int | None = None
    away_goals: int | None = None


@dataclass(frozen=True)
class Quote:
    fixture_id: int
    bookmaker: str
    ts: str
    home_o: float
    draw_o: float
    away_o: float


@dataclass
class Leg:
    fixture: Fixture
    side: Side
    odds: float
    model_p: float
    consensus_p: float
    blended_p: float
    eff_p: float
    eligible_2up: bool = False
    ever2up_p: float | None = None

    def to_json(self) -> dict:
        return {
            "fixture_id": self.fixture.id,
            "league": self.fixture.league,
            "home": self.fixture.home,
            "away": self.fixture.away,
            "kickoff": self.fixture.kickoff,
            "side": self.side.value,
            "odds": self.odds,
            "model_p": round(self.model_p, 4),
            "consensus_p": round(self.consensus_p, 4),
            "blended_p": round(self.blended_p, 4),
            "eff_p": round(self.eff_p, 4),
            "eligible_2up": self.eligible_2up,
        }


@dataclass
class Slip:
    date: str
    legs: list[Leg] = field(default_factory=list)
    total_odds: float = 1.0
    joint_p: float = 1.0
    eff_joint_p: float = 1.0
    bonus_pct: float = 0.0
    stake: float = 0.0
    mode: str = ""
    status: SlipStatus = SlipStatus.PENDING

    @property
    def eff_total_odds(self) -> float:
        return self.total_odds * (1.0 + self.bonus_pct)

    @property
    def ev(self) -> float:
        return self.eff_joint_p * self.eff_total_odds - 1.0


@dataclass(frozen=True)
class Settlement:
    slip_id: int
    result: str
    via_2up: bool
    payout: float
    bonus_paid: float
    settled_at: str


@dataclass
class GovernorState:
    mode: GovernorMode = GovernorMode.PAPER_FLOOR
    tier_idx: int = 0
    demoted: bool = False
    consec_losses: int = 0
    high_watermark: float = 0.0


@dataclass(frozen=True)
class StakeDecision:
    stake: float
    state: GovernorState
    reason: str


@dataclass(frozen=True)
class TeamRatings:
    att_h: float
    def_h: float
    att_a: float
    def_a: float
    n_home: float
    n_away: float
