"""
Voice API — KOL Studio Phase 2: write in the KOL's voice + score similarity.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.services.voice_service import VoiceService

router = APIRouter(prefix="/voice")


class VoiceGenerateRequest(BaseModel):
    persona_id: str
    topic: str = Field(..., min_length=1)
    content_type: str = Field(default="post")


class VoiceScoreRequest(BaseModel):
    persona_id: str
    text: str = Field(..., min_length=1)


@router.post(
    "/generate",
    summary="✍️ Viết bài đúng giọng KOL + chấm % giống",
    description="Dùng Persona DNA để viết bài theo chủ đề, đúng văn phong KOL, "
                "kèm điểm tương đồng phong cách (semantic + style + đặc ngữ).",
)
async def generate(
    data: VoiceGenerateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await VoiceService(db).generate(
            data.persona_id, data.topic, data.content_type
        )
    except LookupError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/score",
    summary="📐 Chấm điểm 1 đoạn text có giống giọng KOL không",
)
async def score(
    data: VoiceScoreRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await VoiceService(db).score(data.persona_id, data.text)
    except LookupError as e:
        raise HTTPException(status_code=409, detail=str(e))
