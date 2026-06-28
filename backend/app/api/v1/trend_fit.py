"""
Trend-Fit API — KOL Studio Phase 4: brand-safe trend matching.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.services.trend_fit_service import TrendFitService

router = APIRouter(prefix="/trend-fit")


class TrendFitRequest(BaseModel):
    persona_id: str
    sources: list[str] | None = None  # tiktok | instagram | reddit | x
    top_k: int = Field(default=10, ge=1, le=15)


@router.post(
    "/analyze",
    summary="🔥 Trend nào hợp brand KOL (có nên đu không)",
    description="Lấy trend rồi chấm độ hợp thương hiệu dựa trên Persona DNA: "
                "verdict nên đu / cân nhắc / nên tránh + lý do + góc tiếp cận.",
)
async def analyze(
    data: TrendFitRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await TrendFitService(db).analyze(
            persona_id=data.persona_id, sources=data.sources, top_k=data.top_k
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
