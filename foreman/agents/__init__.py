"""Agents — specialized LLM-backed actors with bounded scope.

Each agent has:
    - a versioned system prompt (in foreman/llm/prompts/)
    - a bounded tool registry (only tools its domain needs)
    - a memory namespace (it reads/writes facts scoped to its domain)
    - a clear domain it refuses to leave

Agents communicate only through the event bus + shared memory, never by
calling each other directly. This keeps domain boundaries clean and
makes each agent independently testable.
"""
