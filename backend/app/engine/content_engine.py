"""
Content Engine — Phase 3: Auto-generate social media content.

Generates captions, hashtags, and content plans based on:
- Persona's personality and style
- Recent memories and life events
- Current trends (when Trend Engine is active)
"""

from __future__ import annotations

from typing import Any

from app.core.llm import generate_json
from app.utils.prompt_templates import CONTENT_GENERATION_SYSTEM


class ContentEngine:
    """
    Generates social media content in the persona's unique voice.
    """

    @staticmethod
    def _build_persona_context(persona: Any) -> str:
        """Build persona context string for content generation."""
        traits = persona.personality.get("traits", [])
        interests = persona.interests
        return f"""- Tên: {persona.name}
- Tuổi: {persona.age}
- Nghề: {persona.occupation}
- Tính cách: {', '.join(traits) if traits else 'đa dạng'}
- Sở thích: {', '.join(interests) if interests else 'đa dạng'}
- Giọng điệu: {persona.personality.get('tone', 'tự nhiên')}
- Cách nói: {persona.personality.get('speaking_style', 'tự nhiên')}"""

    @staticmethod
    def _build_recent_context(
        memories: list[Any] | None = None,
        life_events: list[Any] | None = None,
    ) -> str:
        """Build recent context string."""
        parts = []

        if memories:
            mem_lines = []
            for m in memories[:5]:
                mem_lines.append(f"  - {m.content[:200]}")
            parts.append("Ký ức gần đây:\n" + "\n".join(mem_lines))

        if life_events:
            ev_lines = []
            for e in life_events[:5]:
                ev_lines.append(f"  - {e.title}: {e.description or ''}")
            parts.append("Sự kiện gần đây:\n" + "\n".join(ev_lines))

        return "\n\n".join(parts) if parts else "Chưa có hoạt động gần đây."

    @staticmethod
    async def generate_caption(
        persona: Any,
        content_type: str = "caption",
        topic_hint: str = "",
        memories: list[Any] | None = None,
        life_events: list[Any] | None = None,
        creativity: float = 0.8,
    ) -> dict[str, Any]:
        """
        Generate a social media caption in the persona's voice.

        Args:
            persona: Persona ORM object
            content_type: caption | story | reel_caption | tweet
            topic_hint: Optional topic suggestion
            memories: Recent memories for context
            life_events: Recent life events for context
            creativity: LLM temperature

        Returns:
            Dict with: caption, hashtags, mood, best_time_to_post
        """
        length_hints = {
            "caption": "vừa phải (100-300 từ)",
            "story": "ngắn (50-100 từ)",
            "reel_caption": "ngắn gọn, catchy (30-80 từ)",
            "tweet": "rất ngắn (dưới 280 ký tự)",
        }

        system_prompt = CONTENT_GENERATION_SYSTEM.format(
            persona_name=persona.name,
            persona_context=ContentEngine._build_persona_context(persona),
            recent_context=ContentEngine._build_recent_context(memories, life_events),
            content_type=content_type,
            tone=persona.personality.get("tone", "tự nhiên"),
            topic_hint=topic_hint or "Tự do (dựa trên cuộc sống hiện tại)",
            length_hint=length_hints.get(content_type, "vừa phải"),
        )

        result = await generate_json(
            system_prompt=system_prompt,
            user_prompt=f"Hãy viết một bài {content_type} cho tôi.",
            temperature=creativity,
            use_lite=True,  # GPT-4o-mini đủ tốt cho caption
        )

        result.setdefault("hashtags", [])
        result.setdefault("mood", "bình thường")
        result.setdefault("best_time_to_post", "19:00")

        return result

    @staticmethod
    async def generate_content_batch(
        persona: Any,
        count: int = 5,
        content_types: list[str] | None = None,
        creativity: float = 0.8,
    ) -> list[dict[str, Any]]:
        """
        Generate a batch of content posts for scheduling.

        Args:
            persona: Persona ORM object
            count: Number of posts to generate
            content_types: Types to generate (defaults to mix)
            creativity: LLM temperature

        Returns:
            List of content dicts
        """
        if content_types is None:
            content_types = ["caption", "caption", "caption", "story", "reel_caption"]

        results = []
        for i in range(count):
            ct = content_types[i % len(content_types)]
            content = await ContentEngine.generate_caption(
                persona=persona,
                content_type=ct,
                topic_hint="",
                creativity=creativity,
            )
            content["content_type"] = ct
            results.append(content)

        return results
