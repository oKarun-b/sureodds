from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def migrate(conn: sqlite3.Connection, migrations_dir: str | Path = "migrations") -> None:
    d = Path(migrations_dir)
    if not d.exists():
        raise FileNotFoundError(f"migrations dir not found: {d}")
    for f in sorted(d.glob("*.sql")):
        conn.executescript(f.read_text(encoding="utf-8"))
    conn.commit()
