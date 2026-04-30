"""Agent base class.

In v0.2 this is intentionally minimal — just enough shape to make Aria
feel like more than a function. v0.3 expands it with tool registries
and memory namespaces.
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path

from foreman.llm.client import LLMClient

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "llm" / "prompts"


class Agent(ABC):
    """Abstract base for specialized LLM-backed agents."""

    name: str
    color_key: str  # key into foreman.ui.theme.AGENT_COLORS
    prompt_file: str  # filename within foreman/llm/prompts/

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def _load_prompt(self) -> str:
        path = PROMPTS_DIR / self.prompt_file
        if not path.exists():
            raise FileNotFoundError(f"Missing prompt file: {path}")
        return path.read_text(encoding="utf-8").strip()
