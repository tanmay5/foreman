"""Nat — ticket triage agent.

Domain: Linear and Jira tickets. Escalates security/migration labels,
deep-triages individual tickets on request.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from foreman.agents.base import Agent
from foreman.connectors.linear import Issue


class Nat(Agent):
    name = "nat"
    color_key = "nat"
    prompt_file = "nat_triage.txt"

    async def triage_issue(self, issue: Issue) -> str:
        system = self._load_prompt()
        payload: dict[str, Any] = {
            "identifier": issue.identifier,
            "title": issue.title,
            "state": issue.state,
            "priority_label": issue.priority_label,
            "labels": issue.labels,
            "description": (issue.description or "")[:1500],
            "age_days": _age_days(issue.created_at),
        }
        return await self._llm.ask(system, json.dumps(payload), max_tokens=700)


def _age_days(iso_ts: str) -> int:
    if not iso_ts:
        return 0
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return 0
    return max(0, (datetime.now(timezone.utc) - dt).days)
