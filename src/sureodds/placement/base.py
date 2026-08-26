from __future__ import annotations

from typing import Protocol

from ..core.models import Slip


class Receipt:
    def __init__(
        self,
        ok: bool,
        bet_id: str | None = None,
        screenshot: bytes | None = None,
        error: str | None = None,
    ):
        self.ok = ok
        self.bet_id = bet_id
        self.screenshot = screenshot
        self.error = error


class PlacementDriver(Protocol):
    def place(self, slip: Slip) -> Receipt: ...

    def abort(self) -> None: ...
