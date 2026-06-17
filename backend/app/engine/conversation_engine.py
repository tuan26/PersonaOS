"""
Conversation Engine — the "soul" of a Persona.

Handles:
- Chatting with a persona in-character
- Maintaining persona consistency
- Incorporating memories and life events into responses
- Generating natural, emotionally-rich responses
"""

from __future__ import annotations

from typing import Any

from app.core.llm import generate_text
from app.utils.prompt_templates import PERSONA_CONVERSATION_SYSTEM


class ConversationEngine:
    """
    Manages persona conversations. Each response is generated
    in the persona's unique voice and personality.
    """

    @staticmethod
    def _format_personality(personality: dict[str, Any]) -> str:
        """Format personality dict into readable text for prompts."""
        lines = []

        traits = personality.get("traits", [])
        if traits:
            lines.append(f"- Đặc điểm: {', '.join(traits)}")

        tone = personality.get("tone")
        if tone:
            lines.append(f"- Giọng điệu: {tone}")

        style = personality.get("speaking_style")
        if style:
            lines.append(f"- Cách nói chuyện: {style}")

        quirks = personality.get("quirks", [])
        if quirks:
            lines.append(f"- Thói quen: {', '.join(quirks)}")

        fears = personality.get("fears", [])
        if fears:
            lines.append(f"- Nỗi sợ: {', '.join(fears)}")

        pet = personality.get("pet_phrases", [])
        if pet:
            lines.append(f"- Câu cửa miệng: {', '.join(pet)}")

        values = personality.get("values", [])
        if values:
            lines.append(f"- Giá trị sống: {', '.join(values)}")

        return "\n".join(lines) if lines else "Thân thiện, tự nhiên"

    @staticmethod
    def _format_interests(interests: list[str]) -> str:
        return ", ".join(interests) if interests else "Đa dạng"

    @staticmethod
    def _format_goals(goals: list[dict[str, Any]]) -> str:
        if not goals:
            return "Chưa xác định"
        lines = []
        for g in goals:
            status_map = {
                "in_progress": "🔄 Đang thực hiện",
                "planning": "📋 Đang lên kế hoạch",
                "dreaming": "💭 Ước mơ",
                "completed": "✅ Đã hoàn thành",
            }
            status = status_map.get(g.get("status", ""), g.get("status", ""))
            deadline = g.get("deadline", "")
            lines.append(f"- {g['goal']} ({status}, deadline: {deadline})")
        return "\n".join(lines)

    @staticmethod
    def _format_memories(memories: list[dict[str, Any]]) -> str:
        """Format recent memories for context."""
        if not memories:
            return "Chưa có ký ức đáng nhớ nào gần đây."

        lines = []
        for m in memories[:10]:  # Last 10 memories
            date = m.get("occurred_at", "").strftime("%d/%m/%Y") if hasattr(m.get("occurred_at"), "strftime") else ""
            lines.append(f"- [{m.get('memory_type', '')}] {m.get('content', '')}")
        return "\n".join(lines)

    @staticmethod
    def _format_life_events(events: list[dict[str, Any]]) -> str:
        """Format recent life events for context."""
        if not events:
            return "Cuộc sống đang diễn ra bình thường."

        lines = []
        for e in events[:10]:
            date = e.get("event_date", "").strftime("%d/%m/%Y") if hasattr(e.get("event_date"), "strftime") else ""
            mood = f" (tâm trạng: {e.get('mood_after', '')})" if e.get("mood_after") else ""
            status = "✅" if e.get("is_completed") else "🔄"
            lines.append(f"- {status} {date}: {e.get('title', '')}{mood}")
        return "\n".join(lines)

    @staticmethod
    async def chat(
        persona: Any,  # Persona ORM object
        message: str,
        memories: list[Any] | None = None,
        life_events: list[Any] | None = None,
        extra_context: str = "",
    ) -> str:
        """
        Chat with a persona. Returns their in-character response.

        Args:
            persona: Persona ORM object
            message: User's message
            memories: Recent memories to include as context
            life_events: Recent life events to include
            extra_context: Any additional context (trends, current events, etc.)

        Returns:
            Persona's response text
        """
        # Build system prompt with full persona context
        system_prompt = PERSONA_CONVERSATION_SYSTEM.format(
            persona_name=persona.name,
            persona_age=persona.age,
            persona_gender=persona.gender,
            persona_occupation=persona.occupation,
            persona_location=persona.location,
            persona_personality=ConversationEngine._format_personality(persona.personality),
            persona_interests=ConversationEngine._format_interests(persona.interests),
            persona_goals=ConversationEngine._format_goals(persona.life_goals),
            persona_backstory=persona.backstory or "Chưa có câu chuyện quá khứ.",
            persona_memories=ConversationEngine._format_memories(memories or []),
            persona_life_events=ConversationEngine._format_life_events(life_events or []),
            extra_context=extra_context,
        )

        response = await generate_text(
            system_prompt=system_prompt,
            user_prompt=message,
            temperature=0.85,  # Slightly higher for personality
        )

        return response.strip()
