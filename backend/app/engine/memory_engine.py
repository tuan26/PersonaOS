"""
Memory Engine — Phase 2: Memory + Life Engine

Manages a persona's memory system:
- Storing conversation memories
- Summarizing important events
- Retrieving relevant memories for context
- Managing the persona's timeline
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.llm import generate_text
from app.utils.prompt_templates import MEMORY_SUMMARIZE_SYSTEM


class MemoryEngine:
    """
    Manages persona memories — storage, summarization, retrieval.
    """

    @staticmethod
    async def summarize_conversation(
        persona_name: str,
        user_message: str,
        persona_response: str,
    ) -> tuple[str, float]:
        """
        Summarize a conversation turn into a storable memory.

        Args:
            persona_name: Name of the persona
            user_message: What the user said
            persona_response: How the persona replied

        Returns:
            (summary_text, importance_score)
        """
        system_prompt = MEMORY_SUMMARIZE_SYSTEM.format(persona_name=persona_name)

        prompt = f"""Hội thoại:
User: {user_message}
{persona_name}: {persona_response}

Tóm tắt thành 1-2 câu và đánh giá mức độ quan trọng (0.0-1.0).
Trả về format: IMPORTANCE: <score>
SUMMARY: <text>"""

        result = await generate_text(
            system_prompt=system_prompt,
            user_prompt=prompt,
            temperature=0.3,
            use_lite=True,  # GPT-4o-mini đủ cho summarization
        )

        # Parse importance and summary
        importance = 0.5
        summary = result

        for line in result.split("\n"):
            if line.upper().startswith("IMPORTANCE:"):
                try:
                    importance = float(line.split(":", 1)[1].strip())
                    importance = max(0.0, min(1.0, importance))
                except ValueError:
                    pass
            elif line.upper().startswith("SUMMARY:"):
                summary = line.split(":", 1)[1].strip()

        return summary, importance

    @staticmethod
    async def generate_life_events(
        persona: Any,
        count: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Generate upcoming life events for a persona's timeline.
        These form the narrative arc of the persona's "life".

        Args:
            persona: Persona ORM object
            count: Number of events to generate

        Returns:
            List of event dicts with: title, description, event_type,
            mood_before, mood_after, days_from_now
        """
        from app.core.llm import generate_json

        system_prompt = f"""Bạn là người lên timeline cuộc sống cho nhân vật {persona.name}.
Dựa trên tính cách, sở thích và mục tiêu của nhân vật, tạo ra các sự kiện trong cuộc sống
sắp tới của họ. Sự kiện phải tự nhiên, có liên kết với nhau, tạo thành một câu chuyện.

Ví dụ:
- Tuần 1: Nhận nuôi mèo
- Tuần 2: Mèo bị ốm
- Tuần 3: Đưa mèo đi khám, mua đồ cho mèo
- Tuần 4: Khoe ảnh mèo khỏe mạnh"""

        user_prompt = f"""Tạo {count} sự kiện sắp tới cho {persona.name}:
- Tuổi: {persona.age}
- Nghề: {persona.occupation}
- Tính cách: {persona.personality.get('traits', [])}
- Sở thích: {persona.interests}
- Mục tiêu: {persona.life_goals}
- Backstory: {persona.backstory}

Trả về JSON array:
```json
[
  {{
    "title": "Tên sự kiện",
    "description": "Mô tả 1-2 câu",
    "event_type": "life|achievement|travel|health|relationship|work|hobby",
    "mood_before": "tâm trạng trước",
    "mood_after": "tâm trạng sau",
    "days_from_now": 3
  }}
]
```

Sự kiện phải LIÊN KẾT với nhau thành một chuỗi câu chuyện."""

        result = await generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
        )

        # Handle both array and {"events": [...]} formats
        events = result if isinstance(result, list) else result.get("events", [])
        return events

    @staticmethod
    def calculate_importance(
        memory_type: str,
        content: str,
        sentiment: str | None = None,
    ) -> float:
        """
        Heuristic importance calculation (fallback when LLM is not used).
        """
        score = 0.3  # Base

        # Memory type weight
        type_weights = {
            "milestone": 0.9,
            "event": 0.7,
            "emotion": 0.6,
            "learning": 0.5,
            "conversation": 0.3,
            "post": 0.4,
        }
        score = type_weights.get(memory_type, 0.3)

        # Content length bonus (longer = potentially more meaningful)
        if len(content) > 200:
            score += 0.1
        if len(content) > 500:
            score += 0.1

        # Sentiment bonus
        if sentiment in ("positive", "negative"):
            score += 0.1

        return min(1.0, score)
