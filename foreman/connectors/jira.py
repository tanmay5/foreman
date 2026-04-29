"""Jira connector.

Polls:
    - Tickets assigned to the user (status, priority, age)
    - Tickets with security/migration labels (escalation path)
    - Tickets the user is watching where status changed

Auth: API token + email. Standard Atlassian flow.
"""

from __future__ import annotations

# TODO(v0.2)
