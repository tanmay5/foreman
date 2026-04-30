"""GitHub connector — v0.1.

Read-only poll of PRs the user cares about. Two queries:
    - PRs awaiting review by the user
    - User's own open PRs

Auth: Personal Access Token (fine-grained recommended).
HTTP: httpx with a small typed wrapper. We deliberately do not depend on
PyGithub — fewer transitive deps, easier to mock, and we use a narrow
slice of the API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from foreman.config import Settings


@dataclass(frozen=True)
class PR:
    """Lightweight PR projection used in briefings."""

    number: int
    title: str
    url: str
    author: str
    repo: str  # "owner/name"
    created_at: str  # ISO 8601 UTC
    updated_at: str  # ISO 8601 UTC


class GitHubError(RuntimeError):
    """Raised when the GitHub API returns a non-2xx response."""


class GitHubConnector:
    """Pluggable GitHub connector. Stateless w.r.t. the user."""

    name = "github"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        token = settings.github_token.get_secret_value()
        self._client = httpx.AsyncClient(
            base_url=f"https://{settings.github_host}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": f"foreman/{settings.github_user}",
            },
            timeout=15.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> GitHubConnector:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # --- public API -------------------------------------------------------

    async def poll_review_requested(self) -> list[PR]:
        """PRs awaiting review from the configured user."""
        q = f"type:pr state:open review-requested:{self._settings.github_user}"
        return await self._search_prs(q)

    async def poll_my_open_prs(self) -> list[PR]:
        """User's own open PRs."""
        q = f"type:pr state:open author:{self._settings.github_user}"
        return await self._search_prs(q)

    async def poll_recently_merged(self, hours: int = 24) -> list[PR]:
        """User's PRs merged within the last `hours` (default 24)."""
        from datetime import datetime, timedelta, timezone
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
        q = f"type:pr is:merged author:{self._settings.github_user} merged:>{since}"
        return await self._search_prs(q)

    async def get_pr_detail(self, repo: str, number: int) -> dict[str, Any]:
        """Fetch a PR's metadata (title, body, author, additions/deletions, etc)."""
        r = await self._client.get(f"/repos/{repo}/pulls/{number}")
        if r.status_code != 200:
            raise GitHubError(f"PR fetch failed [{r.status_code}]: {r.text[:200]}")
        return r.json()

    async def get_pr_diff(self, repo: str, number: int, max_chars: int = 60000) -> str:
        """Fetch the unified diff for a PR. Truncates very large diffs."""
        r = await self._client.get(
            f"/repos/{repo}/pulls/{number}",
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        if r.status_code != 200:
            raise GitHubError(f"Diff fetch failed [{r.status_code}]: {r.text[:200]}")
        text = r.text
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n[...truncated at {max_chars} chars]"
        return text

    async def find_pr_repo(self, number: int) -> str | None:
        """Search the user's review queue + own PRs for a number; return owner/repo if found."""
        for pr in await self.poll_review_requested():
            if pr.number == number:
                return pr.repo
        for pr in await self.poll_my_open_prs():
            if pr.number == number:
                return pr.repo
        return None

    async def health_check(self) -> dict[str, Any]:
        """Verify the token is valid by hitting /user."""
        try:
            r = await self._client.get("/user")
        except httpx.HTTPError as e:
            return {"name": self.name, "ok": False, "error": str(e)}
        ok = r.status_code == 200
        return {
            "name": self.name,
            "ok": ok,
            "status_code": r.status_code,
            "user": r.json().get("login") if ok else None,
            "scopes": r.headers.get("X-OAuth-Scopes", ""),
        }

    # --- internal ---------------------------------------------------------

    async def _search_prs(self, q: str) -> list[PR]:
        r = await self._client.get(
            "/search/issues",
            params={"q": q, "per_page": 30, "sort": "updated", "order": "desc"},
        )
        if r.status_code != 200:
            raise GitHubError(f"GitHub search failed [{r.status_code}]: {r.text[:200]}")
        items = r.json().get("items", [])
        return [_item_to_pr(x) for x in items]


def _item_to_pr(item: dict[str, Any]) -> PR:
    """Map GitHub search/issues item -> PR."""
    url = item["html_url"]
    # html_url shape: https://github.com/{owner}/{repo}/pull/{n}
    parts = url.replace("https://github.com/", "").split("/")
    repo = f"{parts[0]}/{parts[1]}" if len(parts) >= 2 else "?"
    return PR(
        number=item["number"],
        title=item["title"],
        url=url,
        author=(item.get("user") or {}).get("login", "?"),
        repo=repo,
        created_at=item["created_at"],
        updated_at=item["updated_at"],
    )
