"""
Persona API — Phase 1: Persona Engine

Endpoints for creating, managing, and AI-generating personas.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.schemas.persona import (
    PersonaCreate,
    PersonaGenerateRequest,
    PersonaResponse,
    PersonaSummary,
    PersonaUpdate,
    RegenerateFieldRequest,
    RegenerateAvatarRequest,
)
from app.services.persona_service import PersonaService

router = APIRouter(prefix="/personas")


def get_persona_service(db: AsyncSession = Depends(get_db_session)) -> PersonaService:
    return PersonaService(db)


# ── AI Generation ────────────────────────────────────────────────

@router.post(
    "/generate",
    response_model=PersonaResponse,
    status_code=201,
    summary="🤖 AI tạo persona mới",
    description="Dùng AI để tạo một 'con người số' hoàn chỉnh với danh tính, tính cách, câu chuyện cuộc đời.",
)
async def generate_persona(
    request: PersonaGenerateRequest,
    service: PersonaService = Depends(get_persona_service),
):
    """
    **Giai đoạn 1 - Persona Engine**

    Gửi concept ngắn, nhận về persona hoàn chỉnh do AI tạo ra.

    Ví dụ concept: "Dev IT nữ 25t thích Nhật Bản, nuôi mèo, đang tiết kiệm tiền đi Tokyo"
    """
    try:
        persona = await service.generate(request)
        return persona
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tạo persona: {str(e)}")


# ── CRUD ─────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=PersonaResponse,
    status_code=201,
    summary="Tạo persona thủ công",
)
async def create_persona(
    data: PersonaCreate,
    service: PersonaService = Depends(get_persona_service),
):
    """Tạo persona bằng cách điền thủ công (không dùng AI)."""
    return await service.create(data)


@router.get(
    "/",
    response_model=list[PersonaSummary],
    summary="📋 Danh sách tất cả persona",
)
async def list_personas(
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái hoạt động"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: PersonaService = Depends(get_persona_service),
):
    """Lấy danh sách tất cả persona."""
    return await service.list_all(is_active=is_active, limit=limit, offset=offset)


@router.get(
    "/{persona_id}",
    response_model=PersonaResponse,
    summary="🔍 Chi tiết một persona",
)
async def get_persona(
    persona_id: str,
    service: PersonaService = Depends(get_persona_service),
):
    """Lấy thông tin chi tiết của một persona."""
    persona = await service.get(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")
    return persona


@router.patch(
    "/{persona_id}",
    response_model=PersonaResponse,
    summary="✏️ Cập nhật persona",
)
async def update_persona(
    persona_id: str,
    data: PersonaUpdate,
    service: PersonaService = Depends(get_persona_service),
):
    """Cập nhật một phần thông tin persona."""
    persona = await service.update(persona_id, data)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")
    return persona


@router.delete(
    "/{persona_id}",
    status_code=204,
    summary="🗑️ Xóa persona (soft-delete)",
)
async def delete_persona(
    persona_id: str,
    service: PersonaService = Depends(get_persona_service),
):
    """Vô hiệu hóa một persona (soft delete)."""
    success = await service.delete(persona_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")


@router.post(
    "/{persona_id}/regenerate-field",
    summary="🔄 Sinh lại một field bằng AI",
    description="Sinh lại một trường cụ thể (name, appearance, fashion_style, ...) dùng AI, giữ nguyên các trường khác.",
)
async def regenerate_field(
    persona_id: str,
    request: RegenerateFieldRequest,
    service: PersonaService = Depends(get_persona_service),
):
    """Sinh lại một field của persona bằng AI, giữ consistency."""
    persona = await service.get(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")
    try:
        result = await service.regenerate_field(persona, request.field, request.context or {})
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{persona_id}/regenerate-avatar",
    summary="🖼️ Sinh lại ảnh avatar",
    description="Sinh lại ảnh đại diện cho persona. Có thể truyền ảnh tham chiếu mới để vẽ tương tự.",
)
async def regenerate_avatar(
    persona_id: str,
    request: Optional[RegenerateAvatarRequest] = None,
    service: PersonaService = Depends(get_persona_service),
):
    """Sinh lại ảnh avatar cho persona."""
    persona = await service.get(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")
    try:
        ref_url = request.reference_image_url if request else None
        result = await service.regenerate_avatar(persona, ref_url)
        return {"avatar_url": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi sinh avatar: {str(e)}")
