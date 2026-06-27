"""
Memory API — Phase 2: Memory + Life Engine

Endpoints for managing persona memories and life events.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.schemas.memory import (
    LifeEventCreate,
    LifeEventResponse,
    MemoryCreate,
    MemoryResponse,
)
from app.services.memory_service import MemoryService
from app.services.persona_service import PersonaService

router = APIRouter(prefix="/personas/{persona_id}")


def get_memory_service(db: AsyncSession = Depends(get_db_session)) -> MemoryService:
    return MemoryService(db)


def get_persona_service(db: AsyncSession = Depends(get_db_session)) -> PersonaService:
    return PersonaService(db)


# ── Memories ─────────────────────────────────────────────────────

@router.post(
    "/memories",
    response_model=MemoryResponse,
    status_code=201,
    summary="💾 Thêm ký ức cho persona",
)
async def add_memory(
    persona_id: str,
    data: MemoryCreate,
    service: MemoryService = Depends(get_memory_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    """Lưu một ký ức mới cho persona."""
    persona = await persona_service.get(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    return await service.add_memory(
        persona_id=persona_id,
        content=data.content,
        memory_type=data.memory_type,
        memory_category=data.memory_category,
        title=data.title,
        importance=data.importance,
        follower_name=data.follower_name,
        follower_platform=data.follower_platform,
        follower_notes=data.follower_notes,
        metadata=data.metadata_,
        occurred_at=data.occurred_at,
    )


@router.get(
    "/memories",
    response_model=list[MemoryResponse],
    summary="📖 Xem ký ức của persona",
)
async def get_memories(
    persona_id: str,
    memory_type: Optional[str] = Query(None, description="Lọc theo loại ký ức"),
    limit: int = Query(20, ge=1, le=100),
    min_importance: float = Query(0.0, ge=0.0, le=1.0),
    service: MemoryService = Depends(get_memory_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    """Lấy danh sách ký ức gần đây của persona."""
    persona = await persona_service.get(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    return await service.get_recent_memories(
        persona_id=persona_id,
        limit=limit,
        memory_type=memory_type,
        min_importance=min_importance,
    )


# ── Life Events ──────────────────────────────────────────────────

@router.post(
    "/life-events",
    response_model=LifeEventResponse,
    status_code=201,
    summary="📅 Thêm sự kiện cuộc sống",
)
async def add_life_event(
    persona_id: str,
    data: LifeEventCreate,
    service: MemoryService = Depends(get_memory_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    """Thêm một sự kiện vào timeline cuộc sống của persona."""
    persona = await persona_service.get(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    return await service.add_life_event(
        persona_id=persona_id,
        title=data.title,
        description=data.description,
        event_type=data.event_type,
        mood_before=data.mood_before,
        mood_after=data.mood_after,
        event_date=data.event_date,
        is_completed=data.is_completed,
    )


@router.get(
    "/life-events",
    response_model=list[LifeEventResponse],
    summary="📅 Xem timeline cuộc sống",
)
async def get_life_events(
    persona_id: str,
    upcoming_only: bool = Query(False, description="Chỉ lấy sự kiện sắp tới"),
    limit: int = Query(20, ge=1, le=100),
    service: MemoryService = Depends(get_memory_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    """Lấy timeline sự kiện cuộc sống của persona."""
    persona = await persona_service.get(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    if upcoming_only:
        return await service.get_upcoming_events(persona_id, limit)
    return await service.get_recent_events(persona_id, limit)


@router.post(
    "/life-events/generate",
    response_model=list[LifeEventResponse],
    status_code=201,
    summary="🤖 AI tạo timeline sự kiện",
)
async def generate_life_events(
    persona_id: str,
    count: int = Query(3, ge=1, le=10, description="Số sự kiện muốn tạo"),
    service: MemoryService = Depends(get_memory_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    """Dùng AI tạo các sự kiện sắp tới cho persona, liên kết thành câu chuyện."""
    persona = await persona_service.get(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    return await service.generate_life_events(persona, count)
