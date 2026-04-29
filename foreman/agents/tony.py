"""Tony — code review agent.

Domain: PR triage, diff analysis, review-readiness assessment.

Tools:
    get_pr_metadata, get_pr_diff, get_pr_files, get_pr_comments,
    get_file_at_commit, search_repo (for cross-file context)

Tony's job is NOT to write the review for you — it's to (a) tell you
whether a PR is review-ready or has obvious problems, and (b) prep
context so when you sit down to review you're not starting cold.
"""

from __future__ import annotations

# TODO(v0.2)
