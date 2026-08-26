from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..core.models import Fixture, Quote


@dataclass(frozen=True)
class GoalEvent:
    minute: int
    side: str
    own_goal: bool = False


class OddsProvider(Protocol):
    def get_fixtures(self, day: str) -> list[Fixture]: ...

    def get_odds(self, day: str) -> dict[int, list[Quote]]: ...


class ResultsProvider(Protocol):
    def get_result(self, fixture_id: int) -> Fixture: ...

    def get_goal_timeline(self, fixture_id: int) -> list[GoalEvent]: ...


def ever_two_up_from_timeline(events: list[GoalEvent]) -> dict[str, bool]:
    h = a = 0
    eh = ea = False
    for ev in sorted(events, key=lambda e: e.minute):
        scorer = ev.side
        if ev.own_goal:
            scorer = "AWAY" if ev.side == "HOME" else "HOME"
        if scorer == "HOME":
            h += 1
        else:
            a += 1
        if h - a >= 2:
            eh = True
        if a - h >= 2:
            ea = True
    return {"HOME": eh, "AWAY": ea}
