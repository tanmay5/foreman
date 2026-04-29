"""APScheduler-backed scheduler.

Schedules:
    - daily briefing at FOREMAN_BRIEFING_TIME
    - GitHub poll every FOREMAN_PR_POLL_MINUTES
    - Jira poll every FOREMAN_JIRA_POLL_MINUTES
    - Slack poll every FOREMAN_SLACK_POLL_MINUTES
    - nightly memory-synthesis job
"""

from __future__ import annotations

# TODO(v0.5)
