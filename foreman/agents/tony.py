"""Tony — code review agent.

Domain: PR triage, diff analysis, line-specific feedback.
v0.3 surface: review_pr(pr_detail, diff) -> str
"""

from __future__ import annotations

import json
from typing import Any

from foreman.agents.base import Agent


class Tony(Agent):
    name = "tony"
    color_key = "tony"
    prompt_file = "tony_review.txt"

    async def review_pr(self, *, pr_detail: dict[str, Any], diff: str) -> str:
        system = self._load_prompt()
        payload = {
            "number": pr_detail.get("number"),
            "title": pr_detail.get("title", ""),
            "author": (pr_detail.get("user") or {}).get("login", "?"),
            "additions": pr_detail.get("additions", 0),
            "deletions": pr_detail.get("deletions", 0),
            "changed_files": pr_detail.get("changed_files", 0),
            "body": (pr_detail.get("body") or "")[:1500],
            "diff": diff,
        }
        return await self._llm.ask(system, json.dumps(payload), max_tokens=1200)
