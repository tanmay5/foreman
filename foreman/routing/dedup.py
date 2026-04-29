"""Deduplication + rate-limiting.

Uses the seen_items table to suppress duplicate notifications and to
enforce per-source rate limits. Designed so connectors can re-poll
freely without spamming the user.
"""

from __future__ import annotations

# TODO(v0.4)
