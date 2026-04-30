"""Aria — daily synthesis agent.

Domain: morning briefings, end-of-day rollups, top-3-priorities synthesis.
Aria reads from all other agents' outputs (for now: GitHub only) and
produces the human-facing narrative. She is the only agent that gets to
talk in prose — the others produce structured findings that Aria weaves
together.

v0.2 surface: synthesize_briefing(review_prs, my_open_prs) -> str
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from foreman.agents.base import Agent
from foreman.connectors.github import PR


class Aria(Agent):
    name = "aria"
    color_key = "aria"
    prompt_file = "aria_briefing.txt"

    async def synthesize_briefing(
        self,
        *,
        user_name: str,
        review_prs: list[PR],
        my_open_prs: list[PR],
    ) -> str:
        """Produce a short prose briefing from structured PR data."""
        system = self._load_prompt()
        payload = {
            "user_name": user_name,
            "today": datetime.now().date().isoformat(),
            "review_requested": [_pr_summary(p) for p in review_prs],
            "my_open_prs": [_pr_summary(p) for p in my_open_prs],
        }
        return await self._llm.ask(system, json.dumps(payload, indent=2), max_tokens=500)


def _pr_summary(pr: PR) -> dict[str, Any]:
    """Compact dict shape Aria sees. Strip URLs, keep semantics."""
    return {
        "number": pr.number,
        "title": pr.title,
        "repo": pr.repo,
        "author": pr.author,
        "age_days": _age_days(pr.updated_at),
    }


def _age_days(iso_ts: str) -> int:
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return 0
    return max(0, (datetime.now(timezone.utc) - dt).days)
