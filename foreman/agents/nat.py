"""Nat — Jira triage agent.

Domain: ticket analysis, security/migration escalation, blocker detection.

Tools: get_ticket, search_jira, get_related_tickets, get_ticket_history.

Nat's specialty is escalation: when a security or migration ticket lands,
Nat surfaces it immediately, summarizes what's being asked, suggests an
owner if the assignee is ambiguous, and flags blocking dependencies.
"""

from __future__ import annotations

# TODO(v0.2)
