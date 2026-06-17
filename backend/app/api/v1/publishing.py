"""
Publishing API — Phase 4: Publishing Engine

Endpoints for:
- Managing connected social accounts
- Publishing content to multiple platforms
- Checking platform connections
- Fetching post stats
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.schemas.publishing import (
    ConnectionCheckRequest,
    ConnectionCheckResponse,
    PublishAllResponse,
    PublishRequest,
    PublishResultResponse,
    SocialAccountCreate,
    SocialAccountResponse,
)
from app.services.publishing_service import PublishingService
from app.services.persona_service import PersonaService

router = APIRouter(prefix="/publishing")


def get_publishing_service(db: AsyncSession = Depends(get_db_session)) -> PublishingService:
    return PublishingService(db)


def get_persona_service(db: AsyncSession = Depends(get_db_session)) -> PersonaService:
    return PersonaService(db)


# ── Account Management ───────────────────────────────────────────

@router.post(
    "/accounts",
    response_model=SocialAccountResponse,
    status_code=201,
    summary="🔗 Kết nối tài khoản mạng xã hội",
    description="Kết nối tài khoản TikTok, Instagram, Facebook, Threads hoặc X cho persona.",
)
async def connect_account(
    data: SocialAccountCreate,
    service: PublishingService = Depends(get_publishing_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    """Kết nối một tài khoản mạng xã hội với persona."""
    persona = await persona_service.get(data.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    valid_platforms = ["tiktok", "instagram", "facebook", "threads", "x"]
    if data.platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Nền tảng không hợp lệ. Hỗ trợ: {', '.join(valid_platforms)}",
        )

    return await service.connect_account(
        persona_id=data.persona_id,
        platform=data.platform,
        username=data.username,
        access_token=data.access_token,
        platform_user_id=data.platform_user_id,
    )


@router.get(
    "/accounts/{persona_id}",
    response_model=list[SocialAccountResponse],
    summary="📋 Danh sách tài khoản đã kết nối",
)
async def list_accounts(
    persona_id: str,
    service: PublishingService = Depends(get_publishing_service),
):
    """Lấy danh sách tài khoản mạng xã hội đã kết nối của persona."""
    return await service.get_accounts(persona_id)


@router.delete(
    "/accounts/{persona_id}/{platform}",
    status_code=204,
    summary="🔌 Ngắt kết nối tài khoản",
)
async def disconnect_account(
    persona_id: str,
    platform: str,
    service: PublishingService = Depends(get_publishing_service),
):
    """Ngắt kết nối một tài khoản mạng xã hội."""
    success = await service.disconnect_account(persona_id, platform)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")


# ── Publishing ───────────────────────────────────────────────────

@router.post(
    "/publish",
    response_model=PublishAllResponse,
    summary="🚀 Đăng bài lên mạng xã hội",
    description="""
Tự động đăng nội dung lên nhiều nền tảng cùng lúc.

**Hỗ trợ:** TikTok, Instagram, Facebook, Threads, X

**Cách dùng:**
- Cung cấp `content_post_id` để đăng bài đã tạo sẵn
- HOẶC cung cấp trực tiếp `caption`, `media_urls`, `hashtags`
    """,
)
async def publish_post(
    request: PublishRequest,
    service: PublishingService = Depends(get_publishing_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    """Đăng nội dung lên các nền tảng mạng xã hội."""
    persona = await persona_service.get(request.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    # Validate we have either content_post_id or caption
    if not request.content_post_id and not request.caption:
        raise HTTPException(
            status_code=400,
            detail="Cần cung cấp content_post_id hoặc caption",
        )

    results = await service.publish_post(
        persona_id=request.persona_id,
        caption=request.caption or "",
        platforms=request.platforms,
        media_urls=request.media_urls,
        hashtags=request.hashtags,
        content_post_id=request.content_post_id,
        schedule_time=request.schedule_time,
    )

    response_results = [
        PublishResultResponse(
            platform=r.platform.value,
            success=r.success,
            platform_post_id=r.platform_post_id,
            platform_post_url=r.platform_post_url,
            error_message=r.error_message,
        )
        for r in results
    ]

    return PublishAllResponse(
        persona_id=request.persona_id,
        results=response_results,
        total_success=sum(1 for r in results if r.success),
        total_failed=sum(1 for r in results if not r.success),
    )


# ── Connection Check ─────────────────────────────────────────────

@router.post(
    "/check-connection",
    response_model=ConnectionCheckResponse,
    summary="✅ Kiểm tra kết nối nền tảng",
)
async def check_connection(
    request: ConnectionCheckRequest,
    service: PublishingService = Depends(get_publishing_service),
):
    """Kiểm tra xem thông tin đăng nhập nền tảng có hợp lệ không."""
    is_connected = await service.check_connection(
        platform=request.platform,
        access_token=request.access_token,
        platform_user_id=request.platform_user_id,
    )

    return ConnectionCheckResponse(
        platform=request.platform,
        is_connected=is_connected,
        message="Kết nối thành công" if is_connected else "Kết nối thất bại — kiểm tra lại token",
    )


# ── Stats ────────────────────────────────────────────────────────

@router.post(
    "/posts/{social_post_id}/stats",
    summary="📊 Cập nhật thống kê bài đăng",
)
async def fetch_post_stats(
    social_post_id: str,
    service: PublishingService = Depends(get_publishing_service),
):
    """Lấy số liệu tương tác mới nhất cho một bài đã đăng."""
    stats = await service.fetch_post_stats(social_post_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Không thể lấy thống kê")
    return {"social_post_id": social_post_id, "stats": stats}
