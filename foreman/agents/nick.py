"""Nick — Slack digest agent.

Domain: DMs, mentions (later), reply-needed flagging.
v0.7 surface: synthesize_digest(dms) -> str
"""

from __future__ import annotations

import json
from datetime import datetime

from foreman.agents.base import Agent
from foreman.connectors.slack import Message


class Nick(Agent):
    name = "nick"
    color_key = "nick"
    prompt_file = "nick.txt"

    async def synthesize_digest(self, *, dms: list[Message]) -> str:
        system = self._load_prompt()
        payload = {
            "today": datetime.now().date().isoformat(),
            "dms": [{"sender": m.sender, "text": m.text} for m in dms],
        }
        return await self._llm.ask(system, json.dumps(payload), max_tokens=500)
