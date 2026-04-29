"""Slack connector.

Polls (or subscribes via Events API once we have a webhook):
    - DMs received in the last poll window
    - @mentions in channels the user is in
    - Threads where the user has unread replies

Auth: real Slack app with OAuth (Bot + User tokens). NOT cookie scraping.
The cookie + xoxc approach used in V1 violates ToS, breaks weekly, and
is unshippable as a product. v0.3 ships the proper Slack app.

Setup docs: docs/slack-setup.md (TODO)
"""

from __future__ import annotations

# TODO(v0.3): build the Slack app, OAuth flow, polling.
