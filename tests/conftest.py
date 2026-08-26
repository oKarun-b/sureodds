from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sureodds.config import load_config


@pytest.fixture()
def cfg():
    return load_config(ROOT / "config.yaml")
