"""UI theme: per-agent colors and shared styles.

Colors are intentionally consistent so the user learns to recognize
which agent is speaking at a glance.
"""

from __future__ import annotations

# Agent color palette (Tailwind-inspired, terminal-safe).
AGENT_COLORS = {
    "aria": "#10B981",   # emerald — synthesis, calm
    "tony": "#EF4444",   # red — review, attention
    "nat": "#A78BFA",    # violet — analysis
    "nick": "#F59E0B",   # amber — alerts
    "steve": "#60A5FA",  # blue — neutral fallback
}

DIM = "#6B7280"
