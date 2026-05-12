"""Jira connector.

REST API v3 with HTTP Basic auth (email + API token).
API tokens: https://id.atlassian.com/manage-profile/security/api-tokens
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import httpx

from foreman.config import Settings


@dataclass(frozen=True)
class JiraIssue:
    """Lightweight Jira issue projection used in briefings + triage."""
    key: str  # "ABC-123"
    title: str
    state: str
    priority: str
    url: str
    labels: list[str]
    created_at: str
    updated_at: str
    description: str | None = None


class JiraError(RuntimeError):
    """Raised when the Jira API returns an unexpected response."""


class JiraConnector:
    """Pluggable Jira connector. API-token + email auth."""

    name = "jira"

    def __init__(self, settings: Settings) -> None:
        if (
            settings.jira_base_url is None
            or settings.jira_email is None
            or settings.jira_api_token is None
        ):
            raise JiraError(
                "Jira not configured. Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN. "
                "Get a token at https://id.atlassian.com/manage-profile/security/api-tokens"
            )
        token = settings.jira_api_token.get_secret_value()
        auth = base64.b64encode(f"{settings.jira_email}:{token}".encode()).decode()
        self._base_url = settings.jira_base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Basic {auth}",
                "Accept": "application/json",
            },
            timeout=15.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> JiraConnector:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def health_check(self) -> dict[str, Any]:
        try:
            r = await self._client.get(f"{self._base_url}/rest/api/3/myself")
            if r.status_code == 200:
                d = r.json()
                return {
                    "name": self.name,
                    "ok": True,
                    "user": d.get("displayName"),
                    "email": d.get("emailAddress"),
                }
            return {"name": self.name, "ok": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"name": self.name, "ok": False, "error": str(e)}

    async def poll_my_open_issues(self) -> list[JiraIssue]:
        jql = "assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC"
        r = await self._client.get(
            f"{self._base_url}/rest/api/3/search",
            params={
                "jql": jql,
                "maxResults": 30,
                "fields": "summary,status,priority,labels,created,updated",
            },
        )
        if r.status_code != 200:
            raise JiraError(f"Jira search failed [{r.status_code}]: {r.text[:200]}")
        issues_data = r.json().get("issues", []) or []
        return [_to_issue(i, self._base_url) for i in issues_data]

    async def get_issue(self, key: str) -> JiraIssue | None:
        r = await self._client.get(
            f"{self._base_url}/rest/api/3/issue/{key}",
            params={"fields": "summary,status,priority,labels,created,updated,description"},
        )
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            raise JiraError(f"Jira get_issue failed [{r.status_code}]: {r.text[:200]}")
        return _to_issue(r.json(), self._base_url, include_description=True)


def _to_issue(item: dict[str, Any], base_url: str, include_description: bool = False) -> JiraIssue:
    fields = item.get("fields", {}) or {}
    state = ((fields.get("status") or {}).get("name", ""))
    priority = ((fields.get("priority") or {}).get("name", ""))
    labels = fields.get("labels", []) or []
    desc: str | None = None
    if include_description:
        desc_field = fields.get("description")
        desc = _extract_text_from_adf(desc_field) if desc_field else None
    return JiraIssue(
        key=item.get("key", ""),
        title=fields.get("summary", ""),
        state=state,
        priority=priority,
        url=f"{base_url}/browse/{item.get('key', '')}",
        labels=labels,
        created_at=fields.get("created", ""),
        updated_at=fields.get("updated", ""),
        description=desc,
    )


def _extract_text_from_adf(node: Any) -> str:
    """Walk an Atlassian Document Format tree and extract plain text."""
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    parts: list[str] = []
    for child in node.get("content", []) or []:
        parts.append(_extract_text_from_adf(child))
    return " ".join(p for p in parts if p)
