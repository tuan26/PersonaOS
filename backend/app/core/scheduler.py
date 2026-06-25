"""
Scheduler — in-app automation (Phase: auto content generation).

Uses APScheduler (AsyncIOScheduler) running inside the FastAPI process to:
- periodically generate content for every active persona (biased by what has
  performed best — see AnalyticsEngine),
- save it as DRAFT by default for human review,
- optionally auto-publish to connected accounts when AUTO_PUBLISH_ENABLED=True.

The core job is exposed as `run_content_job()` so it can be triggered both by
the cron schedule and manually via the automation API endpoint.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.core.database import async_session_factory

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


# ── Core job (shared by cron + manual trigger) ───────────────────

async def run_content_job(
    publish: Optional[bool] = None,
    posts_per_persona: Optional[int] = None,
) -> dict[str, Any]:
    """
    Generate content for all active personas.

    Args:
        publish: override AUTO_PUBLISH_ENABLED for this run (None = use config).
        posts_per_persona: override SCHEDULER_POSTS_PER_RUN (None = use config).

    Returns a summary dict (counts + per-persona detail).
    """
    from sqlalchemy import select

    from app.models.persona import Persona
    from app.services.content_service import ContentService
    from app.services.memory_service import MemoryService

    do_publish = settings.AUTO_PUBLISH_ENABLED if publish is None else publish
    n = posts_per_persona or settings.SCHEDULER_POSTS_PER_RUN

    summary: dict[str, Any] = {
        "personas_processed": 0,
        "posts_generated": 0,
        "posts_published": 0,
        "publish_mode": do_publish,
        "details": [],
    }

    async with async_session_factory() as db:
        try:
            result = await db.execute(
                select(Persona).where(Persona.is_active == True)  # noqa: E712
            )
            personas = list(result.scalars().all())

            content_service = ContentService(db)
            memory_service = MemoryService(db)

            for persona in personas:
                try:
                    memories = await memory_service.get_recent_memories(
                        persona_id=persona.id, limit=8, min_importance=0.2
                    )
                    events = await memory_service.get_recent_events(
                        persona_id=persona.id, limit=5
                    )

                    posts, insights = await content_service.generate_optimized_batch(
                        persona=persona,
                        count=n,
                        memories=memories,
                        life_events=events,
                    )

                    published = 0
                    if do_publish:
                        published = await _publish_posts(db, persona, posts)

                    summary["personas_processed"] += 1
                    summary["posts_generated"] += len(posts)
                    summary["posts_published"] += published
                    summary["details"].append({
                        "persona": persona.name,
                        "generated": len(posts),
                        "published": published,
                        "optimized": insights.get("learning"),
                    })
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        f"Content job failed for {persona.name}: {str(e)[:200]}"
                    )

            await db.commit()
        except Exception:
            await db.rollback()
            raise

    logger.info(
        f"[scheduler] run_content_job: {summary['posts_generated']} posts for "
        f"{summary['personas_processed']} personas (published={summary['posts_published']})"
    )
    return summary


async def _publish_posts(db: Any, persona: Any, posts: list[Any]) -> int:
    """Publish posts to the persona's connected accounts. Best-effort."""
    from sqlalchemy import select

    from app.engine.publishing_engine import (
        Platform,
        PlatformCredentials,
        PublishingEngine,
    )
    from app.models.social import SocialAccount

    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.persona_id == persona.id,
            SocialAccount.is_connected == True,  # noqa: E712
        )
    )
    accounts = list(result.scalars().all())
    if not accounts:
        return 0

    published = 0
    for post in posts:
        for acc in accounts:
            try:
                creds = PlatformCredentials(
                    platform=Platform(acc.platform),
                    access_token=acc.access_token or "",
                    platform_user_id=acc.platform_user_id,
                )
                res = await PublishingEngine.publish_to_platform(
                    platform=Platform(acc.platform),
                    credentials=creds,
                    caption=post.caption,
                    hashtags=post.hashtags,
                )
                if res.success:
                    published += 1
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Publish failed ({acc.platform}): {str(e)[:150]}")
        # Mark as published if at least attempted under publish mode
        from datetime import datetime, timezone
        post.status = "published"
        post.published_at = datetime.now(timezone.utc)

    return published


# ── Scheduler lifecycle ──────────────────────────────────────────

def start_scheduler() -> None:
    """Start the APScheduler with the daily content job. Idempotent."""
    global _scheduler
    if not settings.SCHEDULER_ENABLED:
        logger.info("[scheduler] disabled via SCHEDULER_ENABLED=false")
        return
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        run_content_job,
        trigger=CronTrigger(hour=settings.SCHEDULER_DAILY_HOUR, minute=0),
        id="daily_content_job",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info(
        f"[scheduler] started — daily content job at "
        f"{settings.SCHEDULER_DAILY_HOUR:02d}:00 UTC "
        f"(auto_publish={settings.AUTO_PUBLISH_ENABLED})"
    )


def shutdown_scheduler() -> None:
    """Stop the scheduler on app shutdown."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("[scheduler] stopped")


def get_scheduler_status() -> dict[str, Any]:
    """Return current scheduler state for the API/dashboard."""
    jobs = []
    if _scheduler is not None:
        for job in _scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "next_run": job.next_run_time.isoformat()
                if job.next_run_time else None,
            })
    return {
        "enabled": settings.SCHEDULER_ENABLED,
        "running": _scheduler is not None,
        "auto_publish": settings.AUTO_PUBLISH_ENABLED,
        "daily_hour_utc": settings.SCHEDULER_DAILY_HOUR,
        "posts_per_run": settings.SCHEDULER_POSTS_PER_RUN,
        "jobs": jobs,
    }
