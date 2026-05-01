"""macOS notification surface.

Uses `osascript` for native notifications. Pluggable so we can add
Linux/Windows backends later (libnotify, win10toast).
"""

from __future__ import annotations

import shutil
import subprocess


def notify(title: str, body: str, sound: str = "Glass") -> None:
    """Fire a native macOS notification. Silently no-ops if osascript missing."""
    if not shutil.which("osascript"):
        return
    safe_title = title.replace('"', '\\"').replace("\n", " ")
    safe_body = body.replace('"', '\\"').replace("\n", " ")
    script = f'display notification "{safe_body}" with title "{safe_title}" sound name "{sound}"'
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)
    except Exception:
        pass
