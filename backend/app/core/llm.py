"""
LLM Client abstraction layer.

Supports:
- OpenAI (GPT-4o, GPT-4o-mini, etc.)
- Anthropic (Claude) — planned
- Local models (Ollama, vLLM) — planned

This abstraction allows swapping LLM providers without changing engine code.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from openai import AsyncOpenAI

from app.config import settings

# ── Global OpenAI client (lazy init) ─────────────────────────────
_openai_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create the async OpenAI client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
    return _openai_client


# ── High-level LLM interface ─────────────────────────────────────

class LLM:
    """
    Unified LLM interface. All engine code calls LLM methods,
    not provider-specific APIs directly.
    """

    @staticmethod
    async def chat(
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 2000,
        response_format: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Send a chat completion request.

        Args:
            messages: List of {"role": "...", "content": "..."}
            model: Model override (defaults to config)
            temperature: Creativity (0.0 = deterministic, 1.0 = creative)
            max_tokens: Max response length
            response_format: Optional {"type": "json_object"} for structured output

        Returns:
            The LLM's text response
        """
        client = get_openai_client()

        kwargs: dict[str, Any] = dict(
            model=model or settings.OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if response_format:
            kwargs["response_format"] = response_format

        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    @staticmethod
    async def chat_json(
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """
        Chat and parse response as JSON. Used when structured output is needed
        (e.g., generating persona profiles, content plans).
        """
        raw = await LLM.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        # Try to parse; strip markdown fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("\n```", 1)[0]

        return json.loads(cleaned)


# ── Convenience ──────────────────────────────────────────────────

async def generate_text(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.8,
    use_lite: bool = False,
) -> str:
    """Quick single-turn generation. Set use_lite=True for GPT-4o-mini."""
    return await LLM.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        model=settings.OPENAI_MODEL_LITE if use_lite else settings.OPENAI_MODEL,
    )


async def generate_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    use_lite: bool = False,
) -> dict[str, Any]:
    """Quick single-turn generation returning JSON. Set use_lite=True for GPT-4o-mini."""
    return await LLM.chat_json(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        model=settings.OPENAI_MODEL_LITE if use_lite else settings.OPENAI_MODEL,
    )
