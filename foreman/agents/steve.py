"""Steve — general fallback agent.

Domain: ad-hoc questions. Has read access to the user's current GitHub state.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from foreman.agents.base import Agent
from foreman.connectors.github import PR


class Steve(Agent):
    name = "steve"
    color_key = "steve"
    prompt_file = "steve.txt"

    async def ask(
        self,
        *,
        question: str,
        review_prs: list[PR],
        my_open_prs: list[PR],
        recent_merged: list[PR],
    ) -> str:
        system = self._load_prompt()
        payload = {
            "today": datetime.now(timezone.utc).date().isoformat(),
            "github_state": {
                "review_requested": [_pr(p) for p in review_prs],
                "my_open_prs": [_pr(p) for p in my_open_prs],
                "recent_merged_24h": [_pr(p) for p in recent_merged],
            },
            "question": question,
        }
        return await self._llm.ask(system, json.dumps(payload), max_tokens=600)


def _pr(p: PR) -> dict[str, object]:
    try:
        dt = datetime.fromisoformat(p.updated_at.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - dt).days
    except ValueError:
        age_days = 0
    return {
        "number": p.number,
        "title": p.title,
        "repo": p.repo,
        "author": p.author,
        "age_days": age_days,
    }
