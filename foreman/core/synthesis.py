"""Memory synthesis — turn episodic events into semantic patterns.

Reads the last N days of agent invocations from SQLite, sends them to
Claude for pattern extraction, stores the resulting patterns in
`memory_patterns`. Briefings then read active patterns and feed them to
Aria so the briefing gets sharper over time.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from foreman.config import Settings
from foreman.core.db import Database
from foreman.llm.client import LLMClient, LLMError

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "llm" / "prompts"


class SynthesisError(RuntimeError):
    pass


async def synthesize_memory(
    settings: Settings,
    db: Database,
    *,
    days: int = 14,
    event_limit: int = 200,
) -> dict[str, Any]:
    """Run a synthesis pass. Returns a summary dict for logging."""
    events = db.recent_events_for_synthesis(days=days, limit=event_limit)
    if not events:
        return {"events_seen": 0, "patterns_extracted": 0, "patterns_kept": 0}

    system = (PROMPTS_DIR / "memory_synthesis.txt").read_text(encoding="utf-8").strip()
    user_payload = {
        "days": days,
        "events": [
            {
                "ts": e.get("ts", "")[:19],
                "kind": e.get("kind"),
                "agent": e.get("agent"),
                "input_summary": (e.get("input_summary") or "")[:300],
                "output": (e.get("output") or "")[:600],
            }
            for e in events
        ],
    }

    async with LLMClient(settings) as llm:
        try:
            raw = await llm.ask(system, json.dumps(user_payload), max_tokens=1500)
        except LLMError as e:
            raise SynthesisError(f"LLM call failed: {e}") from e

    patterns = _parse_patterns(raw)

    # Replace all active patterns with the new set. Simple v1: full refresh.
    # (Future: dedup against existing, decay confidence, etc.)
    db.supersede_all_patterns()
    kept = db.add_patterns(patterns)

    return {
        "events_seen": len(events),
        "patterns_extracted": len(patterns),
        "patterns_kept": kept,
    }


def _parse_patterns(raw: str) -> list[dict[str, str]]:
    """Parse the LLM's JSON output, tolerating a leading code fence."""
    text = raw.strip()
    if text.startswith("```"):
        # strip ``` fence (optionally with `json` lang)
        text = text.lstrip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.lstrip("\n").rstrip("`").rstrip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SynthesisError(f"Synthesis returned non-JSON: {e}\nRaw: {raw[:400]}") from e
    patterns = data.get("patterns") if isinstance(data, dict) else None
    if not isinstance(patterns, list):
        return []
    out: list[dict[str, str]] = []
    for p in patterns:
        if not isinstance(p, dict):
            continue
        pat = str(p.get("pattern", "")).strip()
        ev = str(p.get("evidence_summary", "")).strip()
        if pat:
            out.append({"pattern": pat, "evidence_summary": ev})
    return out
