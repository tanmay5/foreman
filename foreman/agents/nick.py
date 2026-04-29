"""Nick — Slack digest agent.

Domain: DM and mention triage, urgency scoring, reply-needed flagging.

Tools: get_dm_thread, get_channel_context, get_user_profile.

Nick distinguishes between "FYI ping," "needs your input," and "blocking
someone right now." He learns over time which channels and senders the
user actually responds to vs ignores.
"""

from __future__ import annotations

# TODO(v0.3)
