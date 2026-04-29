"""macOS notification surface.

Uses `osascript` to fire native notifications for high-priority events
when the terminal isn't focused. Pluggable so we can add Linux/Windows
backends later (libnotify, win10toast).
"""

from __future__ import annotations

# TODO(v0.5)
