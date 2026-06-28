"""
Content Calendar Service — KOL Studio Phase 3.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.calendar_engine import CalendarEngine, build_pillar_sequence
from app.models.calendar import CalendarItem
from app.services.content_service import ContentService
from app.services.persona_dna_service import PersonaDNAService
from app.services.persona_service import PersonaService


class CalendarService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_items(self, persona_id: str) -> list[CalendarItem]:
        res = await self.db.execute(
            select(CalendarItem)
            .where(CalendarItem.persona_id == persona_id)
            .order_by(CalendarItem.plan_date.asc())
        )
        return list(res.scalars().all())

    async def generate(
        self,
        persona_id: str,
        days: int = 30,
        start_date: date | None = None,
        topics_hint: str = "",
        ratio: tuple[int, int, int] = (70, 20, 10),
    ) -> list[CalendarItem]:
        """Generate a fresh plan. Replaces existing 'planned' items (keeps drafted/done)."""
        persona = await PersonaService(self.db).get(persona_id)
        if not persona:
            raise ValueError("Không tìm thấy persona")
        dna = await PersonaDNAService(self.db).get(persona_id)

        start = start_date or date.today()
        pillars = build_pillar_sequence(days, *ratio)
        ideas = await CalendarEngine.generate_plan(persona, pillars, dna, topics_hint)

        # Clear only un-actioned slots so drafted/done work isn't lost
        await self.db.execute(
            sa_delete(CalendarItem).where(
                CalendarItem.persona_id == persona_id,
                CalendarItem.status == "planned",
            )
        )

        items: list[CalendarItem] = []
        for idea in ideas:
            item = CalendarItem(
                persona_id=persona_id,
                plan_date=start + timedelta(days=idea["day_index"]),
                day_index=idea["day_index"],
                pillar=idea["pillar"],
                topic=idea["topic"],
                title=idea["title"],
                hook=idea["hook"],
                status="planned",
            )
            self.db.add(item)
            items.append(item)

        await self.db.flush()
        for it in items:
            await self.db.refresh(it)
        return items

    async def update_status(self, item_id: str, status: str) -> CalendarItem | None:
        res = await self.db.execute(
            select(CalendarItem).where(CalendarItem.id == item_id)
        )
        item = res.scalar_one_or_none()
        if not item:
            return None
        item.status = status
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def delete_item(self, item_id: str) -> bool:
        res = await self.db.execute(
            select(CalendarItem).where(CalendarItem.id == item_id)
        )
        item = res.scalar_one_or_none()
        if not item:
            return False
        await self.db.delete(item)
        await self.db.flush()
        return True

    async def write_post(self, item_id: str) -> dict[str, Any] | None:
        """Turn a calendar slot into a real voiced draft (linked back to the item)."""
        res = await self.db.execute(
            select(CalendarItem).where(CalendarItem.id == item_id)
        )
        item = res.scalar_one_or_none()
        if not item:
            return None

        persona = await PersonaService(self.db).get(item.persona_id)
        if not persona:
            raise ValueError("Không tìm thấy persona")
        dna = await PersonaDNAService(self.db).get(item.persona_id)

        topic = item.topic or item.title
        caption, hashtags, match = "", [], None

        if dna:
            from app.engine.voice_engine import VoiceEngine
            gen = await VoiceEngine.generate_in_voice(persona, dna, topic, "post")
            caption = gen.get("caption", "")
            hashtags = gen.get("hashtags", [])
            if caption:
                match = await VoiceEngine.score_voice_match(caption, dna)
        else:
            from app.engine.content_engine import ContentEngine
            gen = await ContentEngine.generate_caption(
                persona=persona, content_type="caption", topic_hint=topic
            )
            caption = gen.get("caption", "")
            hashtags = gen.get("hashtags", [])

        # Persist as a draft and link it back to the calendar item
        post = await ContentService(self.db).create_draft(
            persona_id=item.persona_id,
            caption=caption,
            hashtags=hashtags,
            content_type="caption",
            source="calendar",
        )
        # keep the plan date on the post for reference (stays draft = safe)
        post.scheduled_at = None
        item.content_post_id = post.id
        item.status = "drafted"
        await self.db.flush()
        await self.db.refresh(item)

        return {
            "item_id": item.id,
            "content_post_id": post.id,
            "caption": caption,
            "hashtags": hashtags,
            "match": match,
            "status": item.status,
        }
