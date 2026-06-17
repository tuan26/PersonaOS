"""
Chat API — Trò chuyện với AI Persona

Endpoint để chat với persona - đây là nơi persona "sống" và tương tác.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat")


@router.post(
    "/",
    response_model=ChatResponse,
    summary="💬 Chat với AI Persona",
    description="""
Trò chuyện trực tiếp với một persona AI. Persona sẽ phản hồi với đúng tính cách,
giọng điệu, và ký ức của họ — như đang nói chuyện với người thật.

**Ví dụ:**
- "Chị ơi, hôm nay chị thế nào?"
- "Kể em nghe về con mèo của chị đi"
- "Chị có dự định gì cuối tuần này không?"
    """,
)
async def chat_with_persona(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    **Giao tiếp với persona**

    Persona sẽ:
    - Trả lời với đúng giọng điệu và tính cách
    - Nhắc đến ký ức và sự kiện gần đây nếu phù hợp
    - Có cảm xúc thật (vui, buồn, mệt mỏi...)
    - Từ chối nếu "đang bận" (đúng tính cách)
    """
    chat_service = ChatService(db)
    try:
        result = await chat_service.chat(
            persona_id=request.persona_id,
            message=request.message,
            include_memories=request.include_memories,
            include_life_events=request.include_life_events,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi chat: {str(e)}")
