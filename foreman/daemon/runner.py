"""Daemon runner — the asyncio main loop entrypoint.

Wires up: settings -> db -> bus -> connectors -> prioritizer -> agents -> ui.
Started by `foreman run`.
"""

from __future__ import annotations

# TODO(v0.5)
