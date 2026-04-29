"""Prioritization engine — every event passes through here before reaching agents.

Output: (score: float, reason: str). The `reason` is generated text
explaining *why* this matters today, e.g.:

    "PR #123 — Sarah's blocked on this, you usually review hers same-day,
    sprint ends Thursday."

Inputs:
    - source urgency (security ticket > random Jira > PR comment > Slack ping)
    - keyword/label matches against semantic memory
    - engagement history with the actor
    - blocking signals (is someone waiting?)
    - deadlines (sprint end, due date)
    - user-defined rules from foreman.routing.rules
"""

from __future__ import annotations

# TODO(v0.4): scoring fn + LLM-generated reason synthesis.
