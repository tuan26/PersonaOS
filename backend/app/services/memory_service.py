"""
Memory Service — stores and retrieves persona memories.

Phase 2: Memory + Life Engine
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.memory_engine import MemoryEngine
from app.models.memory import LifeEvent, Memory


class MemoryService:
    """Manages persona memories and life events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Memory CRUD ──────────────────────────────────────────────

    async def add_memory(
        self,
        persona_id: str,
        content: str,
        memory_type: str = "conversation",
        title: str | None = None,
        importance: float | None = None,
        metadata: dict[str, Any] | None = None,
        occurred_at: datetime | None = None,
    ) -> Memory:
        """Store a new memory."""
        if importance is None:
            importance = MemoryEngine.calculate_importance(memory_type, content)

        memory = Memory(
            persona_id=persona_id,
            memory_type=memory_type,
            title=title,
            content=content,
            importance=importance,
            metadata_=metadata or {},
            occurred_at=occurred_at or datetime.now(timezone.utc),
        )
        self.db.add(memory)
        await self.db.flush()
        await self.db.refresh(memory)
        return memory

    async def get_recent_memories(
        self,
        persona_id: str,
        limit: int = 20,
        memory_type: str | None = None,
        min_importance: float = 0.0,
    ) -> list[Memory]:
        """Get recent memories for a persona, ordered by recency."""
        stmt = select(Memory).where(
            Memory.persona_id == persona_id,
            Memory.importance >= min_importance,
        )

        if memory_type:
            stmt = stmt.where(Memory.memory_type == memory_type)

        stmt = stmt.order_by(Memory.occurred_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def summarize_and_store(
        self,
        persona_name: str,
        persona_id: str,
        user_message: str,
        persona_response: str,
    ) -> Memory:
        """
        Summarize a conversation turn and store it as a memory.
        Called after each chat interaction.
        """
        summary, importance = await MemoryEngine.summarize_conversation(
            persona_name=persona_name,
            user_message=user_message,
            persona_response=persona_response,
        )

        return await self.add_memory(
            persona_id=persona_id,
            content=summary,
            memory_type="conversation",
            importance=importance,
            metadata={
                "user_message": user_message[:500],
                "persona_response": persona_response[:500],
            },
        )

    # ── Life Events ──────────────────────────────────────────────

    async def add_life_event(
        self,
        persona_id: str,
        title: str,
        event_date: datetime,
        description: str | None = None,
        event_type: str = "life",
        mood_before: str | None = None,
        mood_after: str | None = None,
        is_completed: bool = False,
    ) -> LifeEvent:
        """Add a life event to the persona's timeline."""
        event = LifeEvent(
            persona_id=persona_id,
            title=title,
            description=description,
            event_type=event_type,
            mood_before=mood_before,
            mood_after=mood_after,
            event_date=event_date,
            is_completed=is_completed,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def get_upcoming_events(
        self,
        persona_id: str,
        limit: int = 10,
    ) -> list[LifeEvent]:
        """Get upcoming (future) life events."""
        stmt = (
            select(LifeEvent)
            .where(
                LifeEvent.persona_id == persona_id,
                LifeEvent.is_completed == False,  # noqa: E712
            )
            .order_by(LifeEvent.event_date.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_events(
        self,
        persona_id: str,
        limit: int = 10,
    ) -> list[LifeEvent]:
        """Get recent (past) life events."""
        stmt = (
            select(LifeEvent)
            .where(
                LifeEvent.persona_id == persona_id,
            )
            .order_by(LifeEvent.event_date.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def generate_life_events(
        self,
        persona: Any,
        count: int = 3,
    ) -> list[LifeEvent]:
        """
        AI-generate upcoming life events and persist them.
        """
        from datetime import timedelta

        events_data = await MemoryEngine.generate_life_events(persona, count)

        created_events = []
        for ev in events_data:
            days = ev.get("days_from_now", 7)
            event_date = datetime.now(timezone.utc) + timedelta(days=days)

            event = await self.add_life_event(
                persona_id=persona.id,
                title=ev["title"],
                description=ev.get("description", ""),
                event_type=ev.get("event_type", "life"),
                mood_before=ev.get("mood_before"),
                mood_after=ev.get("mood_after"),
                event_date=event_date,
            )
            created_events.append(event)

        return created_events
