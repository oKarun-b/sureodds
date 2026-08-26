from __future__ import annotations

from datetime import UTC, datetime

import httpx

from ..core.models import Fixture, Quote
from .base import GoalEvent, OddsProvider, ResultsProvider, ever_two_up_from_timeline


class QuotaExceeded(RuntimeError):
    pass


class ApiFootball(OddsProvider, ResultsProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        call_counter=None,
        daily_budget: int = 90,
        timeout: float = 30.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={"x-apisports-key": api_key},
            timeout=timeout,
        )
        self._counter = call_counter
        self._budget = daily_budget

    def _get(self, path: str, params: dict) -> dict:
        if self._counter is not None:
            used = self._counter()
            if used >= self._budget:
                raise QuotaExceeded(f"daily API budget exhausted ({used}/{self._budget})")
        resp = self._client.get(path, params=params)
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("errors"):
            raise RuntimeError(f"API error for {path}: {payload['errors']}")
        if self._counter is not None:
            self._counter()
        return payload

    def get_fixtures(self, day: str) -> list[Fixture]:
        payload = self._get("/fixtures", {"date": day})
        out = []
        for item in payload.get("response", []):
            fx = item["fixture"]
            lg = item["league"]
            teams = item["teams"]
            goals = item.get("goals") or {}
            raw_date = fx["date"]
            if isinstance(raw_date, (int, float)):
                kickoff = datetime.fromtimestamp(int(raw_date), tz=UTC)
                day_str = str(kickoff.date())
                kickoff_s = str(kickoff)
            else:
                kickoff = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
                day_str = str(kickoff.date())
                kickoff_s = str(kickoff)
            out.append(
                Fixture(
                    id=int(fx["id"]),
                    date=day_str,
                    league=f"{lg['country']} - {lg['name']}",
                    home=teams["home"]["name"],
                    away=teams["away"]["name"],
                    kickoff=kickoff_s,
                    status=(fx.get("status") or {}).get("short", "NS"),
                    home_goals=goals.get("home"),
                    away_goals=goals.get("away"),
                )
            )
        return out

    def get_odds(self, day: str) -> dict[int, list[Quote]]:
        result: dict[int, list[Quote]] = {}
        page = 1
        while True:
            try:
                payload = self._get("/odds", {"date": day, "bet": "1", "page": page})
            except RuntimeError as e:
                if "Page parameter" in str(e) and result:
                    break
                raise
            for item in payload.get("response", []):
                fid = int(item["fixture"]["id"])
                quotes = result.setdefault(fid, [])
                for bm in item.get("bookmakers", []):
                    vals = {}
                    for bet in bm.get("bets", []):
                        if int(bet.get("id", 0)) != 1:
                            continue
                        for v in bet.get("values", []):
                            label = v.get("value", "").lower()
                            odd = v.get("odd")
                            if odd in (None, "", "0"):
                                continue
                            key = {"home": "home_o", "draw": "draw_o", "away": "away_o"}.get(label)
                            if key:
                                vals[key] = float(odd)
                    if len(vals) == 3:
                        quotes.append(
                            Quote(
                                fixture_id=fid,
                                bookmaker=bm["name"],
                                ts=str(bm.get("update") or datetime.now(UTC).isoformat()),
                                **vals,
                            )
                        )
            paging = payload.get("paging") or {}
            if page >= int(paging.get("total", 1)):
                break
            page += 1
        return result

    def get_result(self, fixture_id: int) -> Fixture:
        payload = self._get("/fixtures", {"id": fixture_id})
        items = payload.get("response", [])
        if not items:
            raise LookupError(f"fixture {fixture_id} not found")
        item = items[0]
        fx = item["fixture"]
        lg = item["league"]
        teams = item["teams"]
        goals = item.get("goals") or {}
        raw_date = fx["date"]
        if isinstance(raw_date, (int, float)):
            kickoff = datetime.fromtimestamp(int(raw_date), tz=UTC)
            day_str = str(kickoff.date())
            kickoff_s = str(kickoff)
        else:
            kickoff = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
            day_str = str(kickoff.date())
            kickoff_s = str(kickoff)
        return Fixture(
            id=int(fx["id"]),
            date=day_str,
            league=f"{lg['country']} - {lg['name']}",
            home=teams["home"]["name"],
            away=teams["away"]["name"],
            kickoff=kickoff_s,
            status=(fx.get("status") or {}).get("short", "NS"),
            home_goals=goals.get("home"),
            away_goals=goals.get("away"),
        )

    def get_goal_timeline(self, fixture_id: int) -> list[GoalEvent]:
        payload = self._get("/fixtures/events", {"fixture": fixture_id})
        events: list[GoalEvent] = []
        for item in payload.get("response", []):
            if item.get("type") != "Goal":
                continue
            side_hint = item["team"]["name"]
            detail = (item.get("detail") or "").lower()
            own = "own goal" in detail
            events.append(
                GoalEvent(
                    minute=int((item.get("time") or {}).get("elapsed", 0)),
                    side=side_hint,
                    own_goal=own,
                )
            )
        return self._map_sides(fixture_id, events)

    def _map_sides(self, fixture_id: int, events: list[GoalEvent]) -> list[GoalEvent]:
        fx = self.get_result(fixture_id)
        mapped = []
        for ev in events:
            side = "HOME" if ev.side == fx.home else "AWAY"
            mapped.append(GoalEvent(minute=ev.minute, side=side, own_goal=ev.own_goal))
        return mapped

    @staticmethod
    def two_up_flags(goal_events: list[GoalEvent]) -> dict[str, bool]:
        return ever_two_up_from_timeline(goal_events)
