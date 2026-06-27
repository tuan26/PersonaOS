"""
Content API — Phase 3: Content Engine

Endpoints for generating and managing social media content.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.schemas.content import (
    ContentGenerateRequest,
    ContentPostResponse,
    ContentScheduleCreate,
    ContentScheduleResponse,
)
from app.services.content_service import ContentService
from app.services.persona_service import PersonaService

router = APIRouter(prefix="/content")


def get_content_service(db: AsyncSession = Depends(get_db_session)) -> ContentService:
    return ContentService(db)


def get_persona_service(db: AsyncSession = Depends(get_db_session)) -> PersonaService:
    return PersonaService(db)


# ── Content Generation ───────────────────────────────────────────

@router.post(
    "/generate",
    response_model=ContentPostResponse,
    status_code=201,
    summary="🤖 AI tạo nội dung",
    description="Tạo caption/social media post dựa trên tính cách và ký ức của persona.",
)
async def generate_content(
    request: ContentGenerateRequest,
    service: ContentService = Depends(get_content_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    """AI tạo một bài đăng social media cho persona."""
    persona = await persona_service.get(request.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    return await service.generate_post(
        persona=persona,
        content_type=request.content_type,
        topic_hint=request.topic_hint,
        inspired_by_memory_id=request.inspired_by_memory_id,
        inspired_by_event_id=request.inspired_by_event_id,
        creativity=request.creativity,
    )


@router.post(
    "/generate/batch",
    response_model=list[ContentPostResponse],
    status_code=201,
    summary="🤖 AI tạo hàng loạt nội dung",
)
async def generate_content_batch(
    persona_id: str = Query(..., description="Persona ID"),
    count: int = Query(5, ge=1, le=20),
    creativity: float = Query(0.8, ge=0.0, le=1.0),
    service: ContentService = Depends(get_content_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    """AI tạo nhiều bài đăng cùng lúc để lên lịch."""
    persona = await persona_service.get(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    return await service.generate_batch(persona, count, creativity)


# ── Content Management ───────────────────────────────────────────

@router.get(
    "/posts/{persona_id}",
    response_model=list[ContentPostResponse],
    summary="📋 Xem bài đăng của persona",
)
async def list_posts(
    persona_id: str,
    status: Optional[str] = Query(None, description="draft | approved | published"),
    limit: int = Query(20, ge=1, le=100),
    service: ContentService = Depends(get_content_service),
):
    """Lấy danh sách bài đăng của một persona."""
    return await service.get_posts(persona_id, status=status, limit=limit)


@router.patch(
    "/posts/{post_id}/status",
    response_model=ContentPostResponse,
    summary="✅ Cập nhật trạng thái bài đăng",
)
async def update_post_status(
    post_id: str,
    status: str = Query(..., description="draft | approved | scheduled | published"),
    service: ContentService = Depends(get_content_service),
):
    """Cập nhật trạng thái một bài đăng."""
    post = await service.update_status(post_id, status)
    if not post:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài đăng")
    return post


@router.patch(
    "/posts/{post_id}/schedule",
    response_model=ContentPostResponse,
    summary="📅 Lên lịch đăng bài vào ngày giờ cụ thể",
)
async def schedule_post(
    post_id: str,
    scheduled_at: datetime = Query(..., description="Thời điểm đăng (ISO 8601)"),
    service: ContentService = Depends(get_content_service),
):
    """Đặt lịch đăng cho một bài vào thời điểm cụ thể."""
    post = await service.schedule_post(post_id, scheduled_at)
    if not post:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài đăng")
    return post


# ── Schedule ─────────────────────────────────────────────────────

@router.post(
    "/schedule",
    response_model=ContentScheduleResponse,
    status_code=201,
    summary="📅 Tạo lịch đăng bài",
)
async def create_schedule(
    data: ContentScheduleCreate,
    service: ContentService = Depends(get_content_service),
):
    """Tạo lịch đăng bài tự động cho persona."""
    return await service.create_schedule(
        persona_id=data.persona_id,
        posts_per_day=data.posts_per_day,
        preferred_times=data.preferred_times,
    )


@router.get(
    "/schedule/{persona_id}",
    response_model=ContentScheduleResponse,
    summary="📅 Xem lịch đăng bài",
)
async def get_schedule(
    persona_id: str,
    service: ContentService = Depends(get_content_service),
):
    """Lấy cấu hình lịch đăng bài của persona."""
    schedule = await service.get_schedule(persona_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Chưa có lịch đăng bài")
    return schedule
