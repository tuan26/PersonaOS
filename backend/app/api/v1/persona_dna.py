"""
Persona DNA API — KOL Studio Phase 1: Personal Brand Memory Engine.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.models.persona_dna import PersonaDNA  # noqa: F401 (register table)
from app.schemas.persona_dna import DNAAnalyzeRequest, PersonaDNAResponse
from app.services.persona_dna_service import PersonaDNAService
from app.services.persona_service import PersonaService

router = APIRouter(prefix="/persona-dna")


@router.post(
    "/analyze",
    response_model=PersonaDNAResponse,
    summary="🧬 Phân tích DNA văn phong từ bài cũ",
    description="Đọc kho bài đăng cũ → trích Persona DNA (tính cách, đặc ngữ, "
                "cấu trúc bài, style metrics) và lưu lại cho persona.",
)
async def analyze_dna(
    data: DNAAnalyzeRequest,
    db: AsyncSession = Depends(get_db_session),
):
    persona = await PersonaService(db).get(data.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")
    posts = [p for p in data.posts if p and p.strip()]
    if not posts:
        raise HTTPException(status_code=400, detail="Cần ít nhất 1 bài đăng có nội dung")
    return await PersonaDNAService(db).analyze_and_store(
        persona_id=data.persona_id, posts=posts, persona_name=persona.name
    )


@router.get(
    "/{persona_id}",
    response_model=PersonaDNAResponse,
    summary="🧬 Xem DNA đã phân tích",
)
async def get_dna(
    persona_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    dna = await PersonaDNAService(db).get(persona_id)
    if not dna:
        raise HTTPException(status_code=404, detail="Persona chưa có DNA. Hãy phân tích bài cũ trước.")
    return dna
