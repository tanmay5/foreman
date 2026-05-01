"""Linear connector.

GraphQL API. Single API key (from linear.app/settings/account/security),
no OAuth flow required for personal use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from foreman.config import Settings


@dataclass(frozen=True)
class Issue:
    """Lightweight Linear issue projection used in briefings + triage."""
    identifier: str  # "ABC-123"
    title: str
    state: str
    state_type: str  # backlog | unstarted | started | completed | canceled | triage
    priority: int
    priority_label: str
    url: str
    labels: list[str]
    created_at: str
    updated_at: str
    description: str | None = None


class LinearError(RuntimeError):
    """Raised when the Linear API returns an unexpected response."""


_OPEN_ISSUES_QUERY = """
query MyOpenIssues {
  viewer {
    assignedIssues(
      filter: { state: { type: { nin: ["completed", "canceled"] } } }
      first: 30
      orderBy: updatedAt
    ) {
      nodes {
        identifier
        title
        priority
        priorityLabel
        state { name type }
        url
        labels { nodes { name } }
        createdAt
        updatedAt
      }
    }
  }
}
"""

_ISSUE_DETAIL_QUERY = """
query IssueDetail($id: String!) {
  issue(id: $id) {
    identifier
    title
    description
    priority
    priorityLabel
    state { name type }
    url
    labels { nodes { name } }
    createdAt
    updatedAt
  }
}
"""

_VIEWER_QUERY = "query { viewer { id name email } }"


class LinearConnector:
    """Pluggable Linear connector. Stateless w.r.t. the user."""

    name = "linear"

    def __init__(self, settings: Settings) -> None:
        if settings.linear_api_key is None:
            raise LinearError(
                "LINEAR_API_KEY is not set. Get one from "
                "https://linear.app/settings/account/security"
            )
        token = settings.linear_api_key.get_secret_value()
        self._client = httpx.AsyncClient(
            base_url="https://api.linear.app",
            headers={"Authorization": token, "Content-Type": "application/json"},
            timeout=15.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> LinearConnector:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def _gql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        r = await self._client.post(
            "/graphql",
            json={"query": query, "variables": variables or {}},
        )
        if r.status_code != 200:
            raise LinearError(f"Linear API failed [{r.status_code}]: {r.text[:200]}")
        body = r.json()
        if "errors" in body:
            raise LinearError(f"Linear GraphQL errors: {body['errors']}")
        return body.get("data") or {}

    async def health_check(self) -> dict[str, Any]:
        try:
            data = await self._gql(_VIEWER_QUERY)
            viewer = data.get("viewer") or {}
            return {"name": self.name, "ok": True, "user": viewer.get("name"), "email": viewer.get("email")}
        except Exception as e:
            return {"name": self.name, "ok": False, "error": str(e)}

    async def poll_my_open_issues(self) -> list[Issue]:
        data = await self._gql(_OPEN_ISSUES_QUERY)
        nodes = (((data.get("viewer") or {}).get("assignedIssues") or {}).get("nodes")) or []
        return [_to_issue(n) for n in nodes]

    async def get_issue(self, identifier: str) -> Issue | None:
        # Linear lookup uses the identifier (e.g. "ABC-123") directly via graphql `issue(id: ...)`
        # The `id` field accepts identifier strings as well.
        data = await self._gql(_ISSUE_DETAIL_QUERY, {"id": identifier})
        node = data.get("issue")
        return _to_issue(node) if node else None


def _to_issue(node: dict[str, Any]) -> Issue:
    state = node.get("state") or {}
    label_nodes = ((node.get("labels") or {}).get("nodes")) or []
    return Issue(
        identifier=node.get("identifier", "?"),
        title=node.get("title", ""),
        state=state.get("name", ""),
        state_type=state.get("type", ""),
        priority=int(node.get("priority") or 0),
        priority_label=node.get("priorityLabel", ""),
        url=node.get("url", ""),
        labels=[ln.get("name", "") for ln in label_nodes if ln.get("name")],
        created_at=node.get("createdAt", ""),
        updated_at=node.get("updatedAt", ""),
        description=node.get("description"),
    )
