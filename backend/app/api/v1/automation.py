"""
Automation API — control the in-app scheduler & view engagement insights.

- Inspect/trigger the auto content-generation job.
- View AnalyticsEngine recommendations for a persona (the feedback loop).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_db_session
from app.core.scheduler import (
    get_scheduler_status,
    run_content_job,
    shutdown_scheduler,
    start_scheduler,
)
from app.services.content_service import ContentService

router = APIRouter(prefix="/automation")


@router.post(
    "/control",
    summary="⏯️ Bật/tắt scheduler & chế độ đăng",
    description="Bật/tắt lịch tự động và chế độ đăng thẳng (auto-publish) ngay lúc chạy.",
)
async def control(
    enable_scheduler: Optional[bool] = Query(None, description="Bật/tắt scheduler"),
    auto_publish: Optional[bool] = Query(None, description="Bật/tắt đăng tự động"),
):
    """Toggle the scheduler and/or auto-publish at runtime."""
    if auto_publish is not None:
        settings.AUTO_PUBLISH_ENABLED = auto_publish
    if enable_scheduler is not None:
        settings.SCHEDULER_ENABLED = enable_scheduler
        if enable_scheduler:
            start_scheduler()
        else:
            shutdown_scheduler()
    return get_scheduler_status()


@router.get(
    "/status",
    summary="⚙️ Trạng thái scheduler",
    description="Xem scheduler có đang chạy không, giờ chạy job hằng ngày, chế độ đăng bài.",
)
async def scheduler_status():
    """Get the current scheduler status."""
    return get_scheduler_status()


@router.post(
    "/run",
    summary="▶️ Chạy job sinh nội dung ngay",
    description="Sinh nội dung cho tất cả persona đang hoạt động. Mặc định lưu nháp; "
                "đặt publish=true để đăng thẳng lên tài khoản đã kết nối.",
)
async def run_now(
    publish: Optional[bool] = Query(
        None, description="Ghi đè chế độ đăng (None = theo config). true=đăng thẳng, false=lưu nháp"
    ),
    posts_per_persona: Optional[int] = Query(
        None, ge=1, le=10, description="Số bài/persona (None = theo config)"
    ),
):
    """Manually trigger the content generation job."""
    try:
        summary = await run_content_job(
            publish=publish, posts_per_persona=posts_per_persona
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi chạy job: {str(e)}")


@router.get(
    "/insights/{persona_id}",
    summary="📊 Insights tương tác của persona",
    description="Phân tích bài đăng cũ → đề xuất content mix, khung giờ, hashtag tốt nhất.",
)
async def persona_insights(
    persona_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Get engagement insights & recommendations for a persona."""
    service = ContentService(db)
    return await service.get_insights(persona_id)
