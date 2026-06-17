"""
Story API — The heart of PersonaOS.

Endpoints for generating and managing persona life stories.
Flow: Persona → Story Engine → Memory → Content → Publish → Community
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.services.story_service import StoryService
from app.services.persona_service import PersonaService

router = APIRouter(prefix="/stories")


def get_story_service(db: AsyncSession = Depends(get_db_session)) -> StoryService:
    return StoryService(db)


def get_persona_service(db: AsyncSession = Depends(get_db_session)) -> PersonaService:
    return PersonaService(db)


@router.post(
    "/generate",
    summary="📖 AI Tạo Story cho Persona",
    description="""
**Story Engine — Trái tim PersonaOS**

AI sẽ tạo một câu chuyện (story arc) cho cuộc sống của persona:
- Quyết định chuyện gì xảy ra mỗi tuần
- Tạo emotional arc (cảm xúc thay đổi theo thời gian)
- Sinh content ideas cho mỗi cột mốc
- Tự động tạo Life Events trên timeline

**Đây là thứ làm PersonaOS khác biệt:** Nhân vật có CUỘC ĐỜI NHẤT QUÁN.
    """,
)
async def generate_story(
    persona_id: str = Query(..., description="Persona ID"),
    time_scope: str = Query("1_month", description="1_week | 1_month | 3_months"),
    theme: str = Query("lifestyle", description="travel | work | romance | lifestyle | health | hobby"),
    creativity: float = Query(0.75, ge=0.0, le=1.0),
    service: StoryService = Depends(get_story_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    persona = await persona_service.get(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    try:
        story = await service.generate_story(
            persona_id=persona_id,
            time_scope=time_scope,
            theme=theme,
            creativity=creativity,
        )
        return {
            "id": story.id,
            "persona_id": story.persona_id,
            "title": story.title,
            "description": story.description,
            "time_scope": story.time_scope,
            "theme": story.theme,
            "start_date": story.start_date.isoformat(),
            "end_date": story.end_date.isoformat(),
            "emotional_arc": story.emotional_arc,
            "milestones": story.milestones,
            "milestones_count": len(story.milestones),
            "events_generated": story.events_generated,
            "generation_context": story.generation_context,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/active/{persona_id}",
    summary="📖 Xem Story hiện tại của Persona",
)
async def get_active_story(
    persona_id: str,
    service: StoryService = Depends(get_story_service),
):
    story = await service.get_active_story(persona_id)
    if not story:
        raise HTTPException(status_code=404, detail="Chưa có story nào đang hoạt động. Hãy tạo story mới!")

    current_milestone = await service.get_current_milestone(persona_id)

    return {
        "id": story.id,
        "persona_id": story.persona_id,
        "title": story.title,
        "description": story.description,
        "time_scope": story.time_scope,
        "theme": story.theme,
        "emotional_arc": story.emotional_arc,
        "milestones": story.milestones,
        "current_milestone": current_milestone,
        "progress": f"{story.current_milestone}/{len(story.milestones)} milestones",
        "posts_generated": story.posts_generated,
        "is_completed": story.is_completed,
    }


@router.get(
    "/{persona_id}",
    summary="📋 Danh sách Stories của Persona",
)
async def list_stories(
    persona_id: str,
    limit: int = Query(10, ge=1, le=50),
    service: StoryService = Depends(get_story_service),
):
    stories = await service.get_stories(persona_id, limit)
    return [
        {
            "id": s.id,
            "title": s.title,
            "time_scope": s.time_scope,
            "theme": s.theme,
            "start_date": s.start_date.isoformat(),
            "end_date": s.end_date.isoformat(),
            "milestones_count": len(s.milestones),
            "is_active": s.is_active,
            "is_completed": s.is_completed,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in stories
    ]


@router.post(
    "/{story_id}/complete",
    summary="✅ Đánh dấu Story hoàn thành",
)
async def complete_story(
    story_id: str,
    service: StoryService = Depends(get_story_service),
):
    story = await service.complete_story(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Không tìm thấy story")
    return {"message": f"Story '{story.title}' đã hoàn thành"}
