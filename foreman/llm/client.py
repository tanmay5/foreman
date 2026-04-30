"""LLM client — provider abstraction.

Wraps the Anthropic SDK behind an interface that supports a simple
ask(system, user) call for now and tool-use loops in v0.3+.

Behind the interface we can later swap to OpenAI, local Llama, etc.
without touching agent code.
"""

from __future__ import annotations

from typing import Any

from anthropic import AsyncAnthropic

from foreman.config import Settings


class LLMError(RuntimeError):
    """Raised when the LLM call fails or returns an unexpected shape."""


class LLMClient:
    """Async LLM client. Currently Anthropic-only; abstracted for future swap."""

    def __init__(self, settings: Settings) -> None:
        if settings.anthropic_api_key is None:
            raise LLMError(
                "ANTHROPIC_API_KEY is not set. Add it to .env or export it."
            )
        self._settings = settings
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key.get_secret_value())
        self._model = settings.foreman_llm_model

    async def aclose(self) -> None:
        # AsyncAnthropic exposes .close() in newer SDK versions; guard for older ones.
        close = getattr(self._client, "close", None)
        if callable(close):
            await close()

    async def __aenter__(self) -> LLMClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def ask(self, system: str, user: str, max_tokens: int = 600) -> str:
        """Single-turn completion. Returns the model's text output."""
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as e:  # network, auth, rate-limit
            raise LLMError(f"LLM call failed: {e}") from e

        # Normalize: response.content is a list of content blocks; we want text.
        for block in response.content:
            if getattr(block, "type", None) == "text":
                return block.text  # type: ignore[no-any-return]
        raise LLMError("LLM returned no text content.")

    @property
    def model(self) -> str:
        return self._model

    def info(self) -> dict[str, Any]:
        """For doctor command."""
        return {"provider": "anthropic", "model": self._model}
