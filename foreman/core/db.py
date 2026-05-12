"""SQLite persistence layer.

v0.4 schema: events log. Every agent invocation persists here so we can
later (v0.5+) synthesize patterns ("user always closes stale PRs after
Steve's advice", etc).

Sync sqlite3 is fine — single-user CLI, low write rate.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
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

CREATE TABLE IF NOT EXISTS seen_items (
    source TEXT NOT NULL,
    item_id TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    PRIMARY KEY (source, item_id)
);

CREATE TABLE IF NOT EXISTS memory_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,
    evidence_summary TEXT,
    created_at TEXT NOT NULL,
    superseded_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_patterns_active ON memory_patterns(superseded_at);
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

    def load_seen(self, source: str) -> set[str]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT item_id FROM seen_items WHERE source = ?", (source,)
            ).fetchall()
        return {r[0] for r in rows}

    def mark_seen(self, source: str, item_ids: list[str]) -> None:
        if not item_ids:
            return
        ts = datetime.now(timezone.utc).isoformat()
        with self._conn() as c:
            c.executemany(
                "INSERT OR IGNORE INTO seen_items (source, item_id, first_seen) VALUES (?, ?, ?)",
                [(source, i, ts) for i in item_ids],
            )

    def recent_events_for_synthesis(self, days: int = 14, limit: int = 200) -> list[dict[str, Any]]:
        """Pull recent events (kind, agent, input_summary, output) for memory synthesis."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT ts, kind, agent, input_summary, output FROM events "
                "WHERE ts >= ? ORDER BY ts DESC LIMIT ?",
                (cutoff, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def active_patterns(self) -> list[dict[str, Any]]:
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT id, pattern, evidence_summary, created_at FROM memory_patterns "
                "WHERE superseded_at IS NULL ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def supersede_all_patterns(self) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        with self._conn() as c:
            c.execute(
                "UPDATE memory_patterns SET superseded_at = ? WHERE superseded_at IS NULL",
                (ts,),
            )

    def add_patterns(self, patterns: list[dict[str, str]]) -> int:
        """patterns is a list of {pattern, evidence_summary} dicts."""
        if not patterns:
            return 0
        ts = datetime.now(timezone.utc).isoformat()
        rows = [(p.get("pattern", ""), p.get("evidence_summary", ""), ts) for p in patterns]
        with self._conn() as c:
            c.executemany(
                "INSERT INTO memory_patterns (pattern, evidence_summary, created_at) VALUES (?, ?, ?)",
                rows,
            )
        return len(rows)
