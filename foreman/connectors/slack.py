"""Slack connector — user token, DM digest.

v0.7 surface: poll_recent_dms() reads your direct messages from the last
N hours. Mentions search comes in a future release.

Auth: User OAuth Token (xoxp-) from a real Slack app you create at
https://api.slack.com/apps. Required user-token scopes:
    im:read, im:history, users:read, search:read
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from foreman.config import Settings


@dataclass(frozen=True)
class Message:
    sender: str
    text: str
    ts: str
    permalink: str = ""


class SlackError(RuntimeError):
    """Raised when the Slack API returns an unexpected response."""


class SlackConnector:
    """Pluggable Slack connector. User-token only for v0.7."""

    name = "slack"

    def __init__(self, settings: Settings) -> None:
        if settings.slack_user_token is None:
            raise SlackError(
                "SLACK_USER_TOKEN is not set. Create a Slack app at "
                "https://api.slack.com/apps and copy the User OAuth Token (xoxp-...)."
            )
        token = settings.slack_user_token.get_secret_value()
        self._client = httpx.AsyncClient(
            base_url="https://slack.com/api",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )
        self._user_id: str | None = None
        self._user_cache: dict[str, str] = {}

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> SlackConnector:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def _call(self, method: str, **params: Any) -> dict[str, Any]:
        r = await self._client.get(f"/{method}", params=params)
        if r.status_code != 200:
            raise SlackError(f"Slack {method} HTTP {r.status_code}: {r.text[:200]}")
        body = r.json()
        if not body.get("ok"):
            raise SlackError(f"Slack {method} error: {body.get('error', 'unknown')}")
        return body

    async def health_check(self) -> dict[str, Any]:
        try:
            r = await self._call("auth.test")
            self._user_id = r.get("user_id")
            return {
                "name": self.name,
                "ok": True,
                "user": r.get("user"),
                "team": r.get("team"),
            }
        except Exception as e:
            return {"name": self.name, "ok": False, "error": str(e)}

    async def _resolve_user(self, user_id: str) -> str:
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        try:
            r = await self._call("users.info", user=user_id)
            user = r.get("user", {}) or {}
            profile = user.get("profile", {}) or {}
            name = profile.get("display_name") or user.get("real_name") or user.get("name") or user_id
        except SlackError:
            name = user_id
        self._user_cache[user_id] = name
        return name

    async def poll_recent_dms(self, hours: int = 24, limit: int = 30) -> list[Message]:
        """Direct messages received in the last `hours`. Excludes your own messages."""
        if self._user_id is None:
            r = await self._call("auth.test")
            self._user_id = r.get("user_id")

        list_resp = await self._call("conversations.list", types="im", limit=100)
        channels = list_resp.get("channels", []) or []

        oldest_ts = (datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp()
        messages: list[Message] = []

        for ch in channels:
            ch_id = ch.get("id")
            if not ch_id:
                continue
            try:
                history = await self._call(
                    "conversations.history",
                    channel=ch_id,
                    oldest=str(oldest_ts),
                    limit=20,
                )
            except SlackError:
                continue

            for msg in history.get("messages", []) or []:
                user_id = msg.get("user")
                # skip our own messages and bot/system messages
                if not user_id or user_id == self._user_id or msg.get("subtype"):
                    continue
                sender = await self._resolve_user(user_id)
                messages.append(
                    Message(
                        sender=sender,
                        text=(msg.get("text") or "")[:400],
                        ts=msg.get("ts", ""),
                    )
                )
                if len(messages) >= limit:
                    break
            if len(messages) >= limit:
                break

        messages.sort(key=lambda m: m.ts, reverse=True)
        return messages
