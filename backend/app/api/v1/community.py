"""
Community API — Phase 5: Community Engine

Endpoints for:
- Analyzing comment sentiment
- Auto-replying to comments
- Auto-replying to inbox messages
- Managing auto-reply rules
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.schemas.community import (
    AutoReplyResponse,
    AutoReplyRequest,
    AutoReplyRuleCreate,
    AutoReplyRuleResponse,
    CommentAnalyzeRequest,
    CommentAnalyzeResponse,
    InboxReplyRequest,
    InboxReplyResponse,
)
from app.services.community_service import CommunityService
from app.services.persona_service import PersonaService

router = APIRouter(prefix="/community")


def get_community_service(db: AsyncSession = Depends(get_db_session)) -> CommunityService:
    return CommunityService(db)


def get_persona_service(db: AsyncSession = Depends(get_db_session)) -> PersonaService:
    return PersonaService(db)


# ── Comment Analysis ─────────────────────────────────────────────

@router.post(
    "/analyze-comment",
    response_model=CommentAnalyzeResponse,
    summary="🔍 Phân tích bình luận",
    description="Phân tích sentiment và đề xuất hành động cho một bình luận.",
)
async def analyze_comment(
    request: CommentAnalyzeRequest,
    service: CommunityService = Depends(get_community_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    """Phân tích một bình luận: sentiment, hành động nên làm, gợi ý trả lời."""
    persona = await persona_service.get(request.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    analysis = await service.analyze_comment(
        persona_id=request.persona_id,
        comment_content=request.comment_content,
        commenter_name=request.commenter_name,
    )

    return CommentAnalyzeResponse(
        sentiment=analysis.sentiment.value,
        sentiment_score=analysis.sentiment_score,
        action=analysis.action.value,
        suggested_reply=analysis.suggested_reply,
        reason=analysis.reason,
    )


# ── Auto Reply ───────────────────────────────────────────────────

@router.post(
    "/auto-reply",
    response_model=AutoReplyResponse,
    summary="💬 Tự động trả lời bình luận",
    description="""
Tự động phân tích và trả lời hàng loạt bình luận với giọng điệu của persona.

**Flow:**
1. Phân tích sentiment từng bình luận
2. Ưu tiên: câu hỏi > tích cực > trung tính
3. Sinh câu trả lời in-character
4. Thả tim cho bình luận trung tính
    """,
)
async def auto_reply(
    request: AutoReplyRequest,
    service: CommunityService = Depends(get_community_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    """Tự động trả lời hàng loạt bình luận với giọng điệu persona."""
    persona = await persona_service.get(request.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    result = await service.auto_reply_comments(
        persona_id=request.persona_id,
        comments=request.comments,
        max_replies=request.max_replies,
        current_mood=request.current_mood,
    )

    return AutoReplyResponse(**result)


# ── Inbox ────────────────────────────────────────────────────────

@router.post(
    "/inbox-reply",
    response_model=InboxReplyResponse,
    summary="📩 Trả lời tin nhắn riêng",
    description="Sinh câu trả lời tự nhiên cho tin nhắn inbox, với giọng điệu persona.",
)
async def inbox_reply(
    request: InboxReplyRequest,
    service: CommunityService = Depends(get_community_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    """Trả lời tin nhắn inbox với giọng điệu persona."""
    persona = await persona_service.get(request.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    try:
        result = await service.reply_inbox(
            persona_id=request.persona_id,
            sender_name=request.sender_name,
            message_content=request.message_content,
            platform=request.platform,
        )
        return InboxReplyResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Auto Reply Rules ─────────────────────────────────────────────

@router.post(
    "/rules",
    response_model=AutoReplyRuleResponse,
    status_code=201,
    summary="📋 Tạo quy tắc tự động trả lời",
)
async def create_rule(
    data: AutoReplyRuleCreate,
    service: CommunityService = Depends(get_community_service),
):
    """Tạo quy tắc tự động trả lời dựa trên từ khóa/sentiment."""
    return await service.create_rule(
        persona_id=data.persona_id,
        trigger_keywords=data.trigger_keywords,
        reply_template=data.reply_template,
        trigger_sentiment=data.trigger_sentiment,
        is_active=data.is_active,
        priority=data.priority,
    )


@router.get(
    "/rules/{persona_id}",
    response_model=list[AutoReplyRuleResponse],
    summary="📋 Xem quy tắc tự động trả lời",
)
async def list_rules(
    persona_id: str,
    service: CommunityService = Depends(get_community_service),
):
    """Lấy danh sách quy tắc auto-reply của persona."""
    return await service.get_rules(persona_id)


# ── Comments Log ─────────────────────────────────────────────────

@router.get(
    "/comments/{persona_id}",
    summary="📜 Lịch sử bình luận",
)
async def list_comments(
    persona_id: str,
    limit: int = Query(50, ge=1, le=200),
    service: CommunityService = Depends(get_community_service),
):
    """Xem lịch sử bình luận và phản hồi của persona."""
    comments = await service.get_comments(persona_id, limit)
    return [
        {
            "id": c.id,
            "platform": c.platform,
            "author_name": c.author_name,
            "content": c.content,
            "sentiment": c.sentiment,
            "replied": c.replied,
            "reply_content": c.reply_content,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in comments
    ]
