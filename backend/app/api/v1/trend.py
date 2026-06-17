"""
Trend API — Phase 6: Trend Engine

Endpoints for:
- Fetching current trends from all platforms
- Getting persona-specific content recommendations based on trends
- Bulk recommendations for all active personas
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.schemas.trend import (
    TrendFetchRequest,
    TrendRecommendationResponse,
    TrendRecommendListResponse,
    TrendRecommendRequest,
    TrendResponse,
)
from app.services.trend_service import TrendService
from app.services.persona_service import PersonaService

router = APIRouter(prefix="/trends")


async def get_trend_service(db: AsyncSession = Depends(get_db_session)) -> TrendService:
    service = TrendService(db)
    try:
        yield service
    finally:
        await service.close()


def get_persona_service(db: AsyncSession = Depends(get_db_session)) -> PersonaService:
    return PersonaService(db)


# ── Trend Fetching ───────────────────────────────────────────────

@router.post(
    "/fetch",
    response_model=list[TrendResponse],
    summary="🔍 Lấy xu hướng mới nhất",
    description="""
Lấy xu hướng từ các nền tảng:
- **TikTok**: Hashtag, sound, challenge đang trending
- **Instagram**: Chủ đề hot trên explore
- **Reddit**: Bài đăng hot từ các subreddit
- **X (Twitter)**: Trending topics
    """,
)
async def fetch_trends(
    request: TrendFetchRequest,
    service: TrendService = Depends(get_trend_service),
):
    """Lấy danh sách xu hướng mới nhất từ các nền tảng."""
    trends = await service.fetch_trends(
        sources=request.sources,
        count_per_source=request.count_per_source,
        region=request.region,
    )
    return [TrendResponse(**t) for t in trends]


@router.get(
    "/fetch",
    response_model=list[TrendResponse],
    summary="🔍 Lấy xu hướng (GET)",
)
async def fetch_trends_get(
    sources: str = Query("tiktok,instagram,reddit,x", description="Nguồn, cách nhau dấu phẩy"),
    count: int = Query(15, ge=5, le=50),
    region: str = Query("global"),
    service: TrendService = Depends(get_trend_service),
):
    """Lấy xu hướng (GET method, tiện cho test nhanh)."""
    source_list = [s.strip() for s in sources.split(",")]
    trends = await service.fetch_trends(
        sources=source_list,
        count_per_source=count,
        region=region,
    )
    return [TrendResponse(**t) for t in trends]


# ── Persona Recommendations ──────────────────────────────────────

@router.post(
    "/recommend",
    response_model=TrendRecommendListResponse,
    summary="🎯 Gợi ý nội dung theo xu hướng cho persona",
    description="""
**Tính năng chính của Trend Engine:**

1. Lấy tất cả xu hướng từ TikTok, Instagram, Reddit, X
2. Chấm điểm độ phù hợp với persona (dựa trên sở thích, nghề nghiệp, tính cách)
3. Dùng AI sinh caption và hashtag phù hợp
4. Trả về top K gợi ý nội dung

**Kết quả:** Persona luôn đăng nội dung hợp xu hướng → tăng reach.
    """,
)
async def recommend_for_persona(
    request: TrendRecommendRequest,
    service: TrendService = Depends(get_trend_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    """Gợi ý nội dung theo xu hướng cho một persona cụ thể."""
    persona = await persona_service.get(request.persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    result = await service.recommend_for_persona(
        persona_id=request.persona_id,
        sources=request.sources,
        count_per_source=request.count_per_source,
        top_k=request.top_k,
        use_ai=request.use_ai,
    )

    return TrendRecommendListResponse(
        persona_id=result["persona_id"],
        persona_name=result["persona_name"],
        total_trends_analyzed=result["total_trends_analyzed"],
        recommendations=[
            TrendRecommendationResponse(**r)
            for r in result["recommendations"]
        ],
    )


@router.get(
    "/recommend/{persona_id}",
    response_model=TrendRecommendListResponse,
    summary="🎯 Gợi ý nội dung (GET)",
)
async def recommend_get(
    persona_id: str,
    top_k: int = Query(5, ge=1, le=10),
    use_ai: bool = Query(True),
    service: TrendService = Depends(get_trend_service),
    persona_service: PersonaService = Depends(get_persona_service),
):
    """Gợi ý nội dung theo xu hướng (GET, tiện test nhanh)."""
    persona = await persona_service.get(persona_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Không tìm thấy persona")

    result = await service.recommend_for_persona(
        persona_id=persona_id,
        top_k=top_k,
        use_ai=use_ai,
    )

    return TrendRecommendListResponse(
        persona_id=result["persona_id"],
        persona_name=result["persona_name"],
        total_trends_analyzed=result["total_trends_analyzed"],
        recommendations=[
            TrendRecommendationResponse(**r)
            for r in result["recommendations"]
        ],
    )


# ── Bulk Recommendations ─────────────────────────────────────────

@router.get(
    "/recommend-all",
    summary="🌐 Gợi ý cho tất cả persona đang hoạt động",
    description="Lấy xu hướng một lần và sinh gợi ý nội dung cho TẤT CẢ persona đang hoạt động.",
)
async def recommend_all(
    top_k: int = Query(5, ge=1, le=10),
    service: TrendService = Depends(get_trend_service),
):
    """Gợi ý nội dung cho tất cả persona active."""
    results = await service.recommend_all_active(top_k=top_k)
    return {
        "total_personas": len(results),
        "results": results,
    }
