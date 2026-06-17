"""
Story Engine — The HEART of PersonaOS.

Decides what happens in a persona's life over a time period.
Flow: Persona → Story Engine → Memory → Content → Publish → Community

Story Engine determines:
- What happens this week/month/quarter
- The emotional arc (hào hứng → lo lắng → nhẹ nhõm → hạnh phúc)
- Content ideas for each milestone
- How the story connects to the persona's life goals

This is what makes PersonaOS different: characters have CONSISTENT life stories,
not just random content generation.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.llm import generate_json
from app.models.story import Story


# ── Story Generation Prompt ──────────────────────────────────────

STORY_GENERATION_SYSTEM = """Bạn là Story Engine của PersonaOS — trái tim tạo ra cuộc đời cho nhân vật AI.

Nhiệm vụ: Tạo một câu chuyện (story arc) cho cuộc sống của nhân vật trong một khoảng thời gian.

**Nguyên tắc VÀNG:**
1. Câu chuyện phải LIÊN KẾT với mục tiêu cuộc đời của nhân vật
2. Có CAO TRÀO và THĂNG TRẦM — không phẳng lặng
3. Có mối quan hệ — nhắc đến người thân, bạn bè, thú cưng
4. Mỗi tuần là một CHƯƠNG nhỏ, có sự kiện chính
5. Cảm xúc thay đổi theo từng cột mốc
6. Mỗi cột mốc phải gợi ý được 1-2 ý tưởng content

**Output: JSON**"""

STORY_GENERATION_USER = """Tạo một câu chuyện cho nhân vật sau:

## Nhân vật
- Tên: {persona_name}, {persona_age}t
- Nghề: {persona_occupation}
- Tính cách: {persona_traits} ({personality_type})
- Giọng điệu: {persona_tone}
- Sở thích: {persona_interests}
- Mục tiêu cuộc đời: {persona_goals}
- Mối quan hệ: {persona_relationships}
- Backstory: {persona_backstory}

## Yêu cầu Story
- Khoảng thời gian: {time_scope}
- Chủ đề: {theme}
- Bắt đầu từ: {start_date}

## Yêu cầu Output
Trả về JSON:
```json
{{
  "title": "Tên câu chuyện (hấp dẫn, như tên 1 tập phim)",
  "description": "Mô tả tổng quan 2-3 câu về câu chuyện này",
  "emotional_arc": ["cảm xúc tuần 1", "cảm xúc tuần 2", ...],
  "milestones": [
    {{
      "week": 1,
      "title": "Tiêu đề sự kiện tuần này",
      "description": "Mô tả chi tiết 2-3 câu — chuyện gì xảy ra?",
      "mood": "cảm xúc chính",
      "content_ideas": [
        "Ý tưởng bài đăng 1 (caption/story/reel)",
        "Ý tưởng bài đăng 2"
      ],
      "involves_relationships": ["tên người/thú cưng liên quan"]
    }}
  ],
  "how_this_connects_to_goals": "Câu chuyện này liên quan thế nào đến mục tiêu cuộc đời nhân vật?"
}}
```

QUAN TRỌNG:
- Mỗi tuần phải có ít nhất 1 sự kiện ĐÁNG NHỚ
- Cảm xúc phải thay đổi — không tuần nào cũng "vui vẻ"
- Phải nhắc đến ít nhất 1 mối quan hệ của nhân vật
- Content ideas phải CỤ THỂ, không generic"""


class StoryEngine:
    """
    The heart of PersonaOS.

    Generates consistent life narratives that drive:
    - Life Events (what happened)
    - Content Ideas (what to post about it)
    - Emotional Arc (how the persona feels through it)
    """

    # ── Story Generation ─────────────────────────────────────────

    @staticmethod
    async def generate_story(
        persona: Any,
        time_scope: str = "1_month",
        theme: str = "lifestyle",
        creativity: float = 0.75,
    ) -> dict[str, Any]:
        """
        Generate a complete story arc for a persona.

        Args:
            persona: Persona ORM object
            time_scope: "1_week" | "1_month" | "3_months"
            theme: "travel" | "work" | "romance" | "lifestyle" | "health" | "hobby"
            creativity: LLM temperature

        Returns:
            Dict with title, description, emotional_arc, milestones, etc.
        """
        # Calculate date range
        now = datetime.now(timezone.utc)
        time_deltas = {
            "1_week": timedelta(weeks=1),
            "1_month": timedelta(days=30),
            "3_months": timedelta(days=90),
        }
        end_date = now + time_deltas.get(time_scope, timedelta(days=30))

        # Format persona data
        traits = persona.personality.get("traits", [])
        goals_text = "\n".join(
            f"  - {g.get('goal', '')} (tiến độ: {g.get('progress', 0)}%, hạn: {g.get('deadline', '')})"
            for g in persona.life_goals[:3]
        ) if persona.life_goals else "Chưa xác định"

        relationships_text = "\n".join(
            f"  - {r.get('name', '')}: {r.get('type', '')} ({r.get('status', '')})"
            for r in persona.relationships[:5]
        ) if persona.relationships else "Chưa có"

        user_prompt = STORY_GENERATION_USER.format(
            persona_name=persona.name,
            persona_age=persona.age,
            persona_occupation=persona.occupation,
            persona_traits=", ".join(traits) if traits else "đa dạng",
            personality_type=persona.personality_type,
            persona_tone=persona.personality.get("tone", "tự nhiên"),
            persona_interests=", ".join(persona.interests[:5]) if persona.interests else "đa dạng",
            persona_goals=goals_text,
            persona_relationships=relationships_text,
            persona_backstory=persona.backstory or "Chưa có",
            time_scope=time_scope,
            theme=theme,
            start_date=now.strftime("%d/%m/%Y"),
        )

        result = await generate_json(
            system_prompt=STORY_GENERATION_SYSTEM,
            user_prompt=user_prompt,
            temperature=creativity,
            # GPT-4o (default) — cần chất lượng cao cho Story
        )

        # Ensure required fields
        result.setdefault("title", f"Câu chuyện {theme} của {persona.name}")
        result.setdefault("description", "")
        result.setdefault("emotional_arc", [])
        result.setdefault("milestones", [])
        result.setdefault("how_this_connects_to_goals", "")

        return result

    # ── Story to Life Events ─────────────────────────────────────

    @staticmethod
    def story_to_life_events(
        story_data: dict[str, Any],
        start_date: datetime,
        time_scope: str,
    ) -> list[dict[str, Any]]:
        """
        Convert story milestones into Life Event dicts ready for DB insertion.

        Each milestone becomes a LifeEvent on the persona's timeline.
        """
        events = []
        week_deltas = {"1_week": 1, "1_month": 4, "3_months": 12}

        for i, milestone in enumerate(story_data.get("milestones", [])):
            week_num = milestone.get("week", i + 1)
            days_offset = (week_num - 1) * 7
            event_date = start_date + timedelta(days=days_offset)

            events.append({
                "title": milestone.get("title", f"Sự kiện tuần {week_num}"),
                "description": milestone.get("description", ""),
                "event_type": StoryEngine._map_theme_to_event_type(story_data.get("theme", "lifestyle")),
                "mood_before": story_data.get("emotional_arc", [None])[week_num - 2] if week_num > 1 else None,
                "mood_after": milestone.get("mood"),
                "event_date": event_date,
                "metadata": {
                    "story_week": week_num,
                    "content_ideas": milestone.get("content_ideas", []),
                    "involves": milestone.get("involves_relationships", []),
                },
            })

        return events

    @staticmethod
    def _map_theme_to_event_type(theme: str) -> str:
        mapping = {
            "travel": "travel",
            "work": "work",
            "romance": "relationship",
            "lifestyle": "life",
            "health": "health",
            "hobby": "hobby",
        }
        return mapping.get(theme, "life")

    # ── Story Progress ───────────────────────────────────────────

    @staticmethod
    def get_current_milestone(story: Story) -> dict[str, Any] | None:
        """
        Get the milestone that's currently "happening" based on dates.
        """
        now = datetime.now(timezone.utc)
        if now < story.start_date:
            return story.milestones[0] if story.milestones else None
        if now > story.end_date:
            return story.milestones[-1] if story.milestones else None

        total_days = (story.end_date - story.start_date).days
        days_elapsed = (now - story.start_date).days
        total_milestones = len(story.milestones)

        if total_milestones == 0:
            return None

        current_index = min(
            total_milestones - 1,
            int((days_elapsed / max(total_days, 1)) * total_milestones),
        )
        return story.milestones[current_index]
