"""Aria — daily synthesis agent.

Domain: morning briefings, end-of-day rollups, top-3-priorities synthesis.
Aria reads from all configured sources and produces the human-facing
narrative. The only agent that talks in prose; others produce structured
findings that Aria weaves together.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from foreman.agents.base import Agent, PROMPTS_DIR
from foreman.connectors.github import PR
from foreman.connectors.jira import JiraIssue
from foreman.connectors.linear import Issue as LinearIssue
from foreman.connectors.slack import Message as SlackMessage


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
        open_tickets: list[LinearIssue | JiraIssue] | None = None,
        recent_dms: list[SlackMessage] | None = None,
        learned_patterns: list[dict[str, str]] | None = None,
    ) -> str:
        """Produce a short prose briefing across PRs, tickets, Slack, and learned patterns."""
        system = self._load_prompt()
        payload = {
            "user_name": user_name,
            "today": datetime.now().date().isoformat(),
            "review_requested": [_pr_summary(p) for p in review_prs],
            "my_open_prs": [_pr_summary(p) for p in my_open_prs],
            "open_tickets": [_ticket_summary(t) for t in (open_tickets or [])],
            "recent_dms": [{"sender": m.sender, "text": m.text[:200]} for m in (recent_dms or [])][:10],
            "learned_patterns": [
                {"pattern": p.get("pattern", ""), "evidence_summary": p.get("evidence_summary", "")}
                for p in (learned_patterns or [])
            ],
        }
        return await self._llm.ask(system, json.dumps(payload, indent=2), max_tokens=700)

    async def synthesize_standup(
        self,
        *,
        user_name: str,
        yesterday_merged: list[PR],
        today_review: list[PR],
        today_open: list[PR],
    ) -> str:
        """Produce structured standup notes (Yesterday / Today / Blockers)."""
        system = (PROMPTS_DIR / "aria_standup.txt").read_text(encoding="utf-8").strip()
        payload = {
            "user_name": user_name,
            "today": datetime.now().date().isoformat(),
            "yesterday_merged": [_pr_summary(p) for p in yesterday_merged],
            "today_review": [_pr_summary(p) for p in today_review],
            "today_open": [_pr_summary(p) for p in today_open],
        }
        return await self._llm.ask(system, json.dumps(payload, indent=2), max_tokens=500)


def _pr_summary(pr: PR) -> dict[str, Any]:
    return {
        "number": pr.number,
        "title": pr.title,
        "repo": pr.repo,
        "author": pr.author,
        "age_days": _age_days(pr.updated_at),
    }


def _ticket_summary(t: LinearIssue | JiraIssue) -> dict[str, Any]:
    if isinstance(t, LinearIssue):
        return {
            "identifier": t.identifier,
            "source": "linear",
            "title": t.title,
            "state": t.state,
            "priority": t.priority_label,
            "labels": t.labels,
            "age_days": _age_days(t.created_at),
        }
    # Jira
    return {
        "identifier": t.key,
        "source": "jira",
        "title": t.title,
        "state": t.state,
        "priority": t.priority,
        "labels": t.labels,
        "age_days": _age_days(t.created_at),
    }


def _age_days(iso_ts: str) -> int:
    if not iso_ts:
        return 0
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return 0
    return max(0, (datetime.now(timezone.utc) - dt).days)
