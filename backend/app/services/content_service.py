"""
Content Service — generates and manages social media content.

Phase 3: Content Engine
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.analytics_engine import AnalyticsEngine
from app.engine.content_engine import ContentEngine
from app.models.content import ContentPost, ContentSchedule


class ContentService:
    """Manages content generation and scheduling."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Content Generation ───────────────────────────────────────

    async def generate_post(
        self,
        persona: Any,
        content_type: str = "caption",
        topic_hint: str = "",
        inspired_by_memory_id: str | None = None,
        inspired_by_event_id: str | None = None,
        creativity: float = 0.8,
    ) -> ContentPost:
        """Generate a single content post using AI."""
        # Get relevant context
        memories = None
        events = None

        if inspired_by_memory_id:
            from app.models.memory import Memory
            result = await self.db.execute(
                select(Memory).where(Memory.id == inspired_by_memory_id)
            )
            mem = result.scalar_one_or_none()
            memories = [mem] if mem else None

        if inspired_by_event_id:
            from app.models.memory import LifeEvent
            result = await self.db.execute(
                select(LifeEvent).where(LifeEvent.id == inspired_by_event_id)
            )
            ev = result.scalar_one_or_none()
            events = [ev] if ev else None

        # Generate
        content_data = await ContentEngine.generate_caption(
            persona=persona,
            content_type=content_type,
            topic_hint=topic_hint,
            memories=memories,
            life_events=events,
            creativity=creativity,
        )

        # Persist
        post = ContentPost(
            persona_id=persona.id,
            content_type=content_type,
            caption=content_data["caption"],
            hashtags=content_data.get("hashtags", []),
            inspired_by_memory_id=inspired_by_memory_id,
            inspired_by_event_id=inspired_by_event_id,
            generation_context={
                "topic_hint": topic_hint,
                "creativity": creativity,
                "mood": content_data.get("mood"),
            },
            status="draft",
        )
        self.db.add(post)
        await self.db.flush()
        await self.db.refresh(post)
        return post

    async def generate_batch(
        self,
        persona: Any,
        count: int = 5,
        creativity: float = 0.8,
    ) -> list[ContentPost]:
        """Generate multiple content posts at once."""
        content_list = await ContentEngine.generate_content_batch(
            persona=persona,
            count=count,
            creativity=creativity,
        )

        posts = []
        for content_data in content_list:
            post = ContentPost(
                persona_id=persona.id,
                content_type=content_data.get("content_type", "caption"),
                caption=content_data["caption"],
                hashtags=content_data.get("hashtags", []),
                generation_context={
                    "batch": True,
                    "mood": content_data.get("mood"),
                },
                status="draft",
            )
            self.db.add(post)
            posts.append(post)

        await self.db.flush()
        for p in posts:
            await self.db.refresh(p)
        return posts

    # ── Analytics / Feedback Loop ────────────────────────────────

    async def get_insights(self, persona_id: str) -> dict[str, Any]:
        """
        Analyze this persona's past posts and return engagement insights +
        recommendations (content mix, best times, top hashtags).
        """
        result = await self.db.execute(
            select(ContentPost)
            .where(ContentPost.persona_id == persona_id)
            .order_by(ContentPost.created_at.desc())
            .limit(200)
        )
        posts = list(result.scalars().all())
        return AnalyticsEngine.analyze(posts)

    @staticmethod
    def _mix_to_types(mix: dict[str, int], count: int) -> list[str]:
        """Expand a content-mix percentage dict into a list of N content types."""
        types: list[str] = []
        for ct, pct in sorted(mix.items(), key=lambda x: x[1], reverse=True):
            n = max(0, round(count * pct / 100))
            types.extend([ct] * n)
        if not types:
            types = ["caption"]
        # pad/trim to exactly `count`
        while len(types) < count:
            types.append(types[len(types) % len(types)] if types else "caption")
        return types[:count]

    async def generate_optimized_batch(
        self,
        persona: Any,
        count: int = 3,
        memories: list[Any] | None = None,
        life_events: list[Any] | None = None,
        creativity: float = 0.8,
    ) -> tuple[list[ContentPost], dict[str, Any]]:
        """
        Generate a batch biased by what has performed best for this persona.
        Returns (posts, insights). Used by the scheduler.
        """
        insights = await self.get_insights(persona.id)
        types = self._mix_to_types(insights["recommended_mix"], count)

        posts: list[ContentPost] = []
        for ct in types:
            content_data = await ContentEngine.generate_caption(
                persona=persona,
                content_type=ct,
                topic_hint="",
                memories=memories,
                life_events=life_events,
                creativity=creativity,
            )
            post = ContentPost(
                persona_id=persona.id,
                content_type=ct,
                caption=content_data["caption"],
                hashtags=content_data.get("hashtags", []),
                generation_context={
                    "auto": True,
                    "optimized": insights["learning"],
                    "mood": content_data.get("mood"),
                },
                status="draft",
            )
            self.db.add(post)
            posts.append(post)

        await self.db.flush()
        for p in posts:
            await self.db.refresh(p)
        return posts, insights

    # ── Content CRUD ─────────────────────────────────────────────

    async def get_posts(
        self,
        persona_id: str,
        status: str | None = None,
        limit: int = 20,
    ) -> list[ContentPost]:
        """Get content posts for a persona."""
        stmt = select(ContentPost).where(ContentPost.persona_id == persona_id)

        if status:
            stmt = stmt.where(ContentPost.status == status)

        stmt = stmt.order_by(ContentPost.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        post_id: str,
        status: str,
    ) -> ContentPost | None:
        """Update a post's status (draft -> approved -> published)."""
        result = await self.db.execute(
            select(ContentPost).where(ContentPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        if not post:
            return None

        post.status = status
        if status == "published":
            from datetime import datetime, timezone
            post.published_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(post)
        return post

    async def delete_post(self, post_id: str) -> bool:
        """Permanently delete a content post."""
        result = await self.db.execute(
            select(ContentPost).where(ContentPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        if not post:
            return False
        await self.db.delete(post)
        await self.db.flush()
        return True

    async def schedule_post(self, post_id: str, scheduled_at):
        """Mark a post as scheduled at a specific datetime."""
        result = await self.db.execute(
            select(ContentPost).where(ContentPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        if not post:
            return None
        post.status = "scheduled"
        post.scheduled_at = scheduled_at
        await self.db.flush()
        await self.db.refresh(post)
        return post

    # ── Schedule ─────────────────────────────────────────────────

    async def create_schedule(
        self,
        persona_id: str,
        posts_per_day: int = 2,
        preferred_times: list[str] | None = None,
    ) -> ContentSchedule:
        """Create a content schedule for a persona."""
        schedule = ContentSchedule(
            persona_id=persona_id,
            posts_per_day=posts_per_day,
            preferred_times=preferred_times or ["08:00", "12:00", "19:00"],
        )
        self.db.add(schedule)
        await self.db.flush()
        await self.db.refresh(schedule)
        return schedule

    async def get_schedule(self, persona_id: str) -> ContentSchedule | None:
        """Get the content schedule for a persona."""
        result = await self.db.execute(
            select(ContentSchedule).where(ContentSchedule.persona_id == persona_id)
        )
        return result.scalar_one_or_none()
