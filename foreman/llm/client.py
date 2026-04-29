"""LLM client — provider abstraction.

Wraps the Anthropic SDK behind an interface that supports:
    - chat(messages, tools=None) -> response
    - stream(messages, tools=None) -> iterator
    - tool_use loop (agent calls tool, we execute, feed result back)

Behind the interface we can later swap to OpenAI, local Llama, etc.
without touching agent code.
"""

from __future__ import annotations

# TODO(v0.1): minimal wrapper around anthropic.Anthropic with tool-use support.
