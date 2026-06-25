"""
Story Service — orchestrates the Story Engine with DB operations.

The Story Engine is the heart of PersonaOS:
Persona → Story Engine → Memory → Content → Publish → Community
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.story_engine import StoryEngine
from app.models.story import Story
from app.models.memory import LifeEvent
from app.services.persona_service import PersonaService


class StoryService:
    """Manages the persona's life story arcs."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.persona_service = PersonaService(db)

    # ── Generate Story ───────────────────────────────────────────

    async def generate_story(
        self,
        persona_id: str,
        time_scope: str = "1_month",
        theme: str = "lifestyle",
        creativity: float = 0.75,
    ) -> Story:
        """
        AI generates a complete story arc for a persona's life.

        Returns a Story with milestones, emotional arc, and content ideas.
        """
        persona = await self.persona_service.get(persona_id)
        if not persona:
            raise ValueError(f"Persona not found: {persona_id}")

        # 1. Generate story via LLM
        story_data = await StoryEngine.generate_story(
            persona=persona,
            time_scope=time_scope,
            theme=theme,
            creativity=creativity,
        )

        # 2. Calculate dates
        now = datetime.now(timezone.utc)
        time_deltas = {
            "1_week": 7, "1_month": 30, "3_months": 90,
        }
        days = time_deltas.get(time_scope, 30)

        # 3. Create Story
        story = Story(
            persona_id=persona_id,
            title=story_data["title"],
            description=story_data.get("description", ""),
            time_scope=time_scope,
            start_date=now,
            end_date=now.replace(day=min(now.day, 28)) if time_scope == "1_month" else now.replace() if True else now,
            theme=theme,
            emotional_arc=story_data.get("emotional_arc", []),
            milestones=story_data.get("milestones", []),
            generation_context={
                "how_connects_to_goals": story_data.get("how_this_connects_to_goals", ""),
            },
        )
        # Fix end_date properly
        from datetime import timedelta
        story.end_date = now + timedelta(days=days)

        self.db.add(story)
        await self.db.flush()

        # 4. Generate Life Events from milestones
        events_data = StoryEngine.story_to_life_events(story_data, story.start_date, time_scope)
        for ev in events_data:
            event = LifeEvent(
                persona_id=persona_id,
                title=ev["title"],
                description=ev.get("description", ""),
                event_type=ev.get("event_type", "life"),
                mood_before=ev.get("mood_before"),
                mood_after=ev.get("mood_after"),
                event_date=ev["event_date"],
            )
            self.db.add(event)

        story.events_generated = len(events_data)
        await self.db.flush()
        await self.db.refresh(story)

        return story

    # ── Story CRUD ───────────────────────────────────────────────

    async def get_active_story(self, persona_id: str) -> Story | None:
        """Get the currently active story for a persona."""
        result = await self.db.execute(
            select(Story)
            .where(
                Story.persona_id == persona_id,
                Story.is_active == True,  # noqa: E712
                Story.is_completed == False,  # noqa: E712
            )
            .order_by(Story.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_stories(
        self,
        persona_id: str,
        limit: int = 10,
    ) -> list[Story]:
        """Get all stories for a persona."""
        result = await self.db.execute(
            select(Story)
            .where(Story.persona_id == persona_id)
            .order_by(Story.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def complete_story(self, story_id: str) -> Story | None:
        """Mark a story as completed."""
        result = await self.db.execute(select(Story).where(Story.id == story_id))
        story = result.scalar_one_or_none()
        if story:
            story.is_completed = True
            story.is_active = False
            await self.db.flush()
            await self.db.refresh(story)
        return story

    async def get_current_milestone(self, persona_id: str) -> dict[str, Any] | None:
        """Get the currently active milestone in the persona's life story."""
        story = await self.get_active_story(persona_id)
        if not story:
            return None
        return StoryEngine.get_current_milestone(story)
