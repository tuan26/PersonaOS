"""
Revenue Plan API — KOL Studio Phase 5: revenue-goal-driven content plan.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.services.revenue_plan_service import RevenuePlanService

router = APIRouter(prefix="/revenue-plan")


class RevenuePlanRequest(BaseModel):
    persona_id: str
    goal_type: str = Field(default="percent", description="percent | amount")
    goal_value: float = Field(default=20.0, ge=0)
    days: int = Field(default=30, ge=7, le=90)


@router.post(
    "/analyze",
    summary="💰 Lập kế hoạch đạt mục tiêu doanh thu affiliate",
    description="Từ dữ liệu doanh thu thật + DNA, AI trả lời 'muốn +X% thì nên "
                "đăng gì': chẩn đoán, toán doanh thu, sản phẩm nên đẩy, kế hoạch bài.",
)
async def analyze(
    data: RevenuePlanRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await RevenuePlanService(db).analyze(
            persona_id=data.persona_id,
            goal_type=data.goal_type,
            goal_value=data.goal_value,
            days=data.days,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
