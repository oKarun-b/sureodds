from __future__ import annotations

from ..core.models import Slip
from .base import Receipt


class BetpawaPlaywright:
    GATE_MESSAGE = (
        "Playwright placer is phase-9 gated: it stays disabled until the paper-trade "
        "gate passes (>=150 slips, calibration inside bands, ROI CI clear of breakeven)."
    )

    def login_and_save_session(self, profile_dir: str) -> None:
        raise NotImplementedError(self.GATE_MESSAGE)

    def place(self, slip: Slip) -> Receipt:
        raise NotImplementedError(self.GATE_MESSAGE)

    def abort(self) -> None:
        pass
