"""
Content Calendar API — KOL Studio Phase 3: 30-day plan with funnel ratio.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.models.calendar import CalendarItem  # noqa: F401 (register table)
from app.schemas.calendar import CalendarGenerateRequest, CalendarItemResponse
from app.services.calendar_service import CalendarService

router = APIRouter(prefix="/calendar")


@router.post(
    "/generate",
    response_model=list[CalendarItemResponse],
    summary="📅 Tạo lịch nội dung (funnel 70/20/10)",
    description="AI lên lịch N ngày, mỗi ngày 1 pillar (kiến thức/story/bán hàng) "
                "theo tỷ lệ funnel, bám DNA & ngách của KOL.",
)
async def generate(
    data: CalendarGenerateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await CalendarService(db).generate(
            persona_id=data.persona_id,
            days=data.days,
            start_date=data.start_date,
            topics_hint=data.topics_hint,
            ratio=(data.knowledge_pct, data.story_pct, data.sales_pct),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{persona_id}",
    response_model=list[CalendarItemResponse],
    summary="📅 Xem lịch nội dung",
)
async def list_items(
    persona_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    return await CalendarService(db).list_items(persona_id)


@router.post(
    "/items/{item_id}/write",
    summary="✍️ Viết bài cho 1 ngày (đúng giọng KOL) → lưu nháp",
)
async def write_post(
    item_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        res = await CalendarService(db).write_post(item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not res:
        raise HTTPException(status_code=404, detail="Không tìm thấy mục lịch")
    return res


@router.patch(
    "/items/{item_id}/status",
    response_model=CalendarItemResponse,
    summary="🔁 Cập nhật trạng thái mục lịch",
)
async def update_status(
    item_id: str,
    status: str = Query(..., description="planned | drafted | done"),
    db: AsyncSession = Depends(get_db_session),
):
    item = await CalendarService(db).update_status(item_id, status)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy mục lịch")
    return item


@router.delete(
    "/items/{item_id}",
    status_code=204,
    summary="🗑️ Xóa mục lịch",
)
async def delete_item(
    item_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    ok = await CalendarService(db).delete_item(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy mục lịch")
