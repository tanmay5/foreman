"""GitHub connector.

Polls:
    - PRs awaiting review by the user
    - User's own open PRs (status, age, blockers)
    - Issues / @mentions in repos the user owns

Auth: Personal Access Token (fine-grained) for v0.1, GitHub App for v1.0.
API client: httpx. We keep our own lightweight wrapper rather than pulling
in PyGithub — fewer dependencies, easier to mock, and we only use a
narrow slice of the API surface.
"""

from __future__ import annotations

# TODO(v0.1): poll_my_open_prs() against GitHub REST API. First end-to-end slice.
