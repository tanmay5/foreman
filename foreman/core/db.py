"""SQLite persistence layer.

Owns the schema and connection pooling for foreman.db. Tables:
    events            — immutable log of every alert produced
    seen_items        — connector dedup keys
    actions           — what the user did with each event
    memory_episodic   — derived facts (response latency, engagement)
    memory_semantic   — synthesized patterns (versioned)
    agent_traces      — every agent invocation, for debugging + eval

Migrations are stored in foreman/core/migrations/ as numbered SQL files
and applied in order on startup.
"""

from __future__ import annotations

# TODO(v0.1): minimal schema + Database class with async connection helper.
