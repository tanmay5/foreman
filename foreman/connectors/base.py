"""Connector protocol.

Every data source plugs in via this contract. Connectors are stateless
with respect to the user — all state lives in the db.
"""

from __future__ import annotations

from typing import Any, Protocol


class Connector(Protocol):
    """A pluggable data source."""

    name: str

    async def poll(self) -> list[Any]:
        """Fetch new items since last poll. Returns events to publish."""
        ...

    async def fetch_detail(self, item_id: str) -> dict[str, Any]:
        """Fetch full detail for a specific item (e.g. PR diff, ticket body)."""
        ...

    async def health_check(self) -> dict[str, Any]:
        """Verify auth + reachability. Used by `foreman doctor`."""
        ...
