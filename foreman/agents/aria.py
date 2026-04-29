"""Aria — daily synthesis agent.

Domain: morning briefings, end-of-day rollups, top-3-priorities synthesis.
Aria reads from all other agents' outputs and produces the human-facing
narrative. She is the only agent that gets to talk in prose — the others
produce structured findings that Aria weaves together.

Tools: read_recent_events, read_priorities, read_user_calendar (future).
"""

from __future__ import annotations

# TODO(v0.1): minimal briefing synthesis using GitHub-only data.
