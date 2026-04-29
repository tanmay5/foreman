"""Agent base class + tool registry primitive.

Agents are constructed with:
    - llm: an LLMClient
    - tools: a list of tool definitions (Anthropic tool-use format)
    - prompt: the system prompt (loaded from foreman/llm/prompts/)
    - memory: a memory handle scoped to this agent's namespace
"""

from __future__ import annotations

# TODO(v0.2): Agent base class with .invoke(event) -> AgentResponse contract.
