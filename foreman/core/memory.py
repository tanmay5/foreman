"""Memory layer — the differentiator.

Two stores:
    Episodic — every alert + the user's action against it. Cheap SQL.
    Semantic — patterns synthesized from episodic data by a nightly LLM job.

The semantic layer is what separates Foreman from a notifier. Examples of
facts the system should converge on:
    - "User responds to PRs from @sarah within 3 hours on average."
    - "User treats labels {security, migration, cve} as drop-everything."
    - "User ignores 80% of #eng-general mentions but replies to all DMs."

Each semantic fact carries provenance (source episodic event ids) so the
user can audit "why does Foreman think that?"
"""

from __future__ import annotations

# TODO(v0.4): episodic write API, semantic synthesis job, query API for prioritizer.
