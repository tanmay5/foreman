"""SQLite persistence layer.

v0.4 schema: events log. Every agent invocation persists here so we can
later (v0.5+) synthesize patterns ("user always closes stale PRs after
Steve's advice", etc).

Sync sqlite3 is fine — single-user CLI, low write rate.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,
    agent TEXT,
    input_summary TEXT,
    output TEXT,
    meta_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
"""


class Database:
    """Thin wrapper around the foreman.db SQLite file."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def log_event(
        self,
        *,
        kind: str,
        agent: str | None,
        input_summary: str,
        output: str,
        meta: dict[str, Any] | None = None,
    ) -> int:
        ts = datetime.now(timezone.utc).isoformat()
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO events (ts, kind, agent, input_summary, output, meta_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ts, kind, agent, input_summary, output, json.dumps(meta or {})),
            )
            return cur.lastrowid or 0

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT id, ts, kind, agent, input_summary, output FROM events "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def count(self) -> int:
        with self._conn() as c:
            return int(c.execute("SELECT COUNT(*) FROM events").fetchone()[0])
