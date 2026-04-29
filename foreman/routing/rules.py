"""User-defined routing rules.

Rules are plain Python functions that take an Event and return a
RoutingDecision. Examples (to be implemented):

    - escalate any security-labeled ticket immediately
    - suppress Slack pings during calendar meetings
    - never re-notify the same PR within 4 hours
    - always notify on PRs from a configured "respond fast" list
"""

from __future__ import annotations

# TODO(v0.4)
