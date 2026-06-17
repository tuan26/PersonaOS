"""
Trend Engine — Phase 6: Detect and leverage social media trends.

Monitors:
- TikTok trending hashtags and sounds
- Instagram trending topics
- Reddit hot posts
- X (Twitter) trending topics

Then suggests content ideas tailored to each persona's niche.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

import httpx

from app.config import settings
from app.core.llm import generate_json
from app.utils.prompt_templates import TREND_ANALYSIS_SYSTEM


# ── Data Types ───────────────────────────────────────────────────

class TrendSource(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    REDDIT = "reddit"
    X = "x"


class TrendCategory(str, Enum):
    HASHTAG = "hashtag"
    SOUND = "sound"
    CHALLENGE = "challenge"
    TOPIC = "topic"
    MEME = "meme"
    NEWS = "news"


@dataclass
class Trend:
    """A detected trend."""
    source: TrendSource
    category: TrendCategory
    title: str
    description: str = ""
    hashtag: str | None = None
    url: str | None = None
    popularity_score: float = 0.0  # 0-100
    engagement_count: int = 0
    trending_since: datetime | None = None
    region: str = "global"
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendRecommendation:
    """A content recommendation based on a trend."""
    trend: Trend
    relevance_score: float  # 0-1 how relevant to persona
    suggested_caption: str
    suggested_hashtags: list[str]
    content_type: str  # caption | reel | story
    reasoning: str


# ── Trend Fetchers ───────────────────────────────────────────────

class TrendFetcher:
    """
    Fetches trends from various platforms.
    Each platform has its own method with appropriate API calls or scraping.
    """

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "PersonaOS/1.0 TrendEngine"
            },
        )

    async def close(self):
        await self.client.aclose()

    # ── TikTok Trends ────────────────────────────────────────────

    async def fetch_tiktok_trends(self, count: int = 20) -> list[Trend]:
        """
        Fetch trending hashtags and topics from TikTok.

        Uses TikTok's public trending API or scraping.
        Note: Full API requires TikTok Research API access.
        """
        trends: list[Trend] = []

        try:
            # TikTok Trending Hashtags endpoint (public-ish)
            response = await self.client.get(
                "https://www.tiktok.com/api/trending/hashtag/list/",
                params={"count": count},
            )

            if response.status_code == 200:
                data = response.json()
                for item in data.get("items", [])[:count]:
                    trends.append(
                        Trend(
                            source=TrendSource.TIKTOK,
                            category=TrendCategory.HASHTAG,
                            title=item.get("title", ""),
                            hashtag=item.get("title", ""),
                            description=item.get("description", ""),
                            popularity_score=item.get("views", 0) / 10000,
                            engagement_count=item.get("views", 0),
                            raw_data=item,
                        )
                    )
        except Exception:
            pass  # Graceful degradation — trends may not be available

        # Fallback: curated trending topics if API fails
        if not trends:
            trends = TrendFetcher._tiktok_fallback_trends()

        return trends

    # ── Instagram Trends ─────────────────────────────────────────

    async def fetch_instagram_trends(self, count: int = 20) -> list[Trend]:
        """Fetch trending topics from Instagram (via Graph API or scraping)."""
        trends: list[Trend] = []

        try:
            # Instagram trending via public explore page scraping
            response = await self.client.get(
                "https://www.instagram.com/api/v1/web/topics/topics_page/",
            )

            if response.status_code == 200:
                data = response.json()
                for topic in data.get("topics", [])[:count]:
                    trends.append(
                        Trend(
                            source=TrendSource.INSTAGRAM,
                            category=TrendCategory.TOPIC,
                            title=topic.get("name", ""),
                            description=topic.get("description", ""),
                            popularity_score=topic.get("score", 0),
                            raw_data=topic,
                        )
                    )
        except Exception:
            pass

        if not trends:
            trends = TrendFetcher._instagram_fallback_trends()

        return trends

    # ── Reddit Trends ─────────────────────────────────────────────

    async def fetch_reddit_trends(
        self,
        subreddits: list[str] | None = None,
        count: int = 20,
    ) -> list[Trend]:
        """
        Fetch hot posts from Reddit.
        Uses Reddit's public JSON API (no auth needed for read-only).
        """
        if subreddits is None:
            subreddits = [
                "VietNam", "tech", "technology", "programming",
                "travel", "fitness", "food", "gaming",
                "cryptocurrency", "entrepreneur",
            ]

        trends: list[Trend] = []

        async def fetch_subreddit(sub: str) -> list[Trend]:
            results = []
            try:
                response = await self.client.get(
                    f"https://www.reddit.com/r/{sub}/hot.json",
                    params={"limit": min(count // len(subreddits) + 2, 10)},
                )

                if response.status_code == 200:
                    data = response.json()
                    for post in data.get("data", {}).get("children", []):
                        post_data = post["data"]
                        score = post_data.get("score", 0)
                        if score > 10:  # Filter low-engagement
                            results.append(
                                Trend(
                                    source=TrendSource.REDDIT,
                                    category=TrendCategory.TOPIC,
                                    title=post_data.get("title", ""),
                                    description=post_data.get("selftext", "")[:300],
                                    url=f"https://reddit.com{post_data.get('permalink', '')}",
                                    popularity_score=min(100, score / 10),
                                    engagement_count=score,
                                    raw_data=post_data,
                                )
                            )
            except Exception:
                pass
            return results

        # Fetch from multiple subreddits in parallel
        tasks = [fetch_subreddit(sub) for sub in subreddits]
        results = await asyncio.gather(*tasks)

        for sub_trends in results:
            trends.extend(sub_trends)

        # Sort by engagement, take top
        trends.sort(key=lambda t: t.engagement_count, reverse=True)
        return trends[:count]

    # ── X (Twitter) Trends ───────────────────────────────────────

    async def fetch_x_trends(
        self,
        woeid: int = 1,  # 1 = Worldwide, 23424977 = US, 23424984 = Vietnam
        count: int = 20,
    ) -> list[Trend]:
        """
        Fetch trending topics from X (Twitter).

        Uses X API v1.1 trends/place endpoint.
        Requires Bearer Token or API key.
        """
        trends: list[Trend] = []

        api_key = settings.X_API_KEY
        if not api_key:
            return TrendFetcher._x_fallback_trends()

        try:
            response = await self.client.get(
                "https://api.x.com/1.1/trends/place.json",
                params={"id": woeid},
                headers={"Authorization": f"Bearer {api_key}"},
            )

            if response.status_code == 200:
                data = response.json()
                for trend_obj in data[0].get("trends", [])[:count]:
                    volume = trend_obj.get("tweet_volume") or 0
                    trends.append(
                        Trend(
                            source=TrendSource.X,
                            category=TrendCategory.HASHTAG,
                            title=trend_obj.get("name", ""),
                            hashtag=trend_obj.get("name", ""),
                            url=trend_obj.get("url", ""),
                            popularity_score=min(100, volume / 1000),
                            engagement_count=volume,
                            raw_data=trend_obj,
                        )
                    )
        except Exception:
            pass

        if not trends:
            trends = TrendFetcher._x_fallback_trends()

        return trends

    # ── Fallback Trends (when APIs unavailable) ──────────────────

    @staticmethod
    def _tiktok_fallback_trends() -> list[Trend]:
        """Curated fallback — common TikTok trends."""
        topics = [
            ("GRWM", "Get Ready With Me"),
            ("DayInMyLife", "Một ngày của tôi"),
            ("POV", "Point of View storytelling"),
            ("LearnOnTikTok", "Content giáo dục"),
            ("FoodTok", "Ẩm thực & nấu ăn"),
            ("TechTok", "Công nghệ & gadgets"),
            ("TravelTok", "Du lịch & khám phá"),
            ("FitnessTok", "Tập luyện & sức khỏe"),
            ("BookTok", "Sách & review"),
            ("PetTok", "Thú cưng"),
        ]
        return [
            Trend(
                source=TrendSource.TIKTOK,
                category=TrendCategory.HASHTAG,
                title=name,
                hashtag=name,
                description=desc,
                popularity_score=60,
            )
            for name, desc in topics
        ]

    @staticmethod
    def _instagram_fallback_trends() -> list[Trend]:
        topics = [
            ("aesthetic", "Phong cách thẩm mỹ, moodboard"),
            ("coffee", "Cà phê & lifestyle"),
            ("outfit", "Thời trang hàng ngày"),
            ("selfcare", "Chăm sóc bản thân"),
            ("homedecor", "Trang trí nhà cửa"),
            ("tech", "Công nghệ & gadgets"),
            ("fitness", "Tập luyện & sức khỏe"),
            ("travel", "Du lịch"),
            ("food", "Ẩm thực"),
            ("mindset", "Phát triển bản thân"),
        ]
        return [
            Trend(
                source=TrendSource.INSTAGRAM,
                category=TrendCategory.TOPIC,
                title=name,
                description=desc,
                popularity_score=60,
            )
            for name, desc in topics
        ]

    @staticmethod
    def _x_fallback_trends() -> list[Trend]:
        topics = [
            ("#AI", "Artificial Intelligence"),
            ("#tech", "Technology"),
            ("#OpenAI", "OpenAI news"),
            ("#crypto", "Cryptocurrency"),
            ("#startup", "Startups"),
            ("#remote", "Remote work"),
            ("#design", "Design trends"),
            ("#developer", "Developer community"),
            ("#travel", "Travel"),
            ("#fitness", "Fitness"),
        ]
        return [
            Trend(
                source=TrendSource.X,
                category=TrendCategory.HASHTAG,
                title=name,
                hashtag=name,
                description=desc,
                popularity_score=55,
            )
            for name, desc in topics
        ]


# ── Trend Engine ─────────────────────────────────────────────────

class TrendEngine:
    """
    Aggregates trends from all platforms and recommends content for personas.

    Flow:
    1. Fetch trends from all sources in parallel
    2. Score relevance for each persona
    3. Generate content recommendations
    """

    def __init__(self):
        self.fetcher = TrendFetcher()

    async def close(self):
        await self.fetcher.close()

    # ── Trend Aggregation ────────────────────────────────────────

    async def fetch_all_trends(
        self,
        sources: list[TrendSource] | None = None,
        count_per_source: int = 15,
        region: str = "global",
    ) -> list[Trend]:
        """
        Fetch trends from all or specified sources in parallel.

        Args:
            sources: Which sources to query (None = all)
            count_per_source: How many trends per source
            region: Geographic region filter
        """
        if sources is None:
            sources = list(TrendSource)

        tasks = []
        for source in sources:
            if source == TrendSource.TIKTOK:
                tasks.append(self.fetcher.fetch_tiktok_trends(count_per_source))
            elif source == TrendSource.INSTAGRAM:
                tasks.append(self.fetcher.fetch_instagram_trends(count_per_source))
            elif source == TrendSource.REDDIT:
                tasks.append(self.fetcher.fetch_reddit_trends(count=count_per_source))
            elif source == TrendSource.X:
                tasks.append(self.fetcher.fetch_x_trends(count=count_per_source))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_trends: list[Trend] = []
        for r in results:
            if isinstance(r, list):
                all_trends.extend(r)

        # Deduplicate by title
        seen = set()
        unique_trends = []
        for trend in all_trends:
            key = trend.title.lower().strip("#")
            if key not in seen:
                seen.add(key)
                unique_trends.append(trend)

        # Sort by popularity
        unique_trends.sort(key=lambda t: t.popularity_score, reverse=True)

        return unique_trends

    # ── Relevance Scoring ────────────────────────────────────────

    @staticmethod
    def score_relevance(trend: Trend, persona: Any) -> float:
        """
        Score how relevant a trend is to a persona (0.0-1.0).

        Based on: matching interests, occupation, personality.
        """
        score = 0.0
        trend_text = f"{trend.title} {trend.description} {trend.hashtag or ''}".lower()

        persona_keywords = set()

        # Add interests
        for interest in persona.interests:
            persona_keywords.update(interest.lower().split())

        # Add occupation keywords
        persona_keywords.update(persona.occupation.lower().split())

        # Add personality traits
        for trait in persona.personality.get("traits", []):
            persona_keywords.update(trait.lower().split())

        # Match
        matches = sum(1 for kw in persona_keywords if kw in trend_text)
        if persona_keywords:
            score = min(1.0, matches / len(persona_keywords) * 2)

        # Boost for exact interest match
        for interest in persona.interests:
            if interest.lower() in trend_text:
                score = min(1.0, score + 0.3)

        # Boost for occupation match
        occ_parts = persona.occupation.lower().split()
        if any(part in trend_text for part in occ_parts):
            score = min(1.0, score + 0.2)

        return round(score, 2)

    # ── Content Recommendation ───────────────────────────────────

    async def recommend_for_persona(
        self,
        persona: Any,
        trends: list[Trend],
        top_k: int = 5,
        use_ai: bool = True,
    ) -> list[TrendRecommendation]:
        """
        Generate content recommendations for a persona based on trends.

        Args:
            persona: Persona ORM object
            trends: List of detected trends
            top_k: Number of recommendations to return
            use_ai: Use LLM for deeper analysis
        """
        # 1. Score relevance
        scored = []
        for trend in trends:
            relevance = self.score_relevance(trend, persona)
            if relevance > 0.1:  # Minimum relevance threshold
                scored.append((trend, relevance))

        # Sort by relevance
        scored.sort(key=lambda x: x[1], reverse=True)
        top_trends = scored[:top_k]

        # 2. Generate content suggestions
        recommendations = []

        if use_ai and top_trends:
            recommendations = await self._ai_recommend(persona, top_trends)
        else:
            # Simple template-based recommendations
            for trend, relevance in top_trends:
                rec = TrendRecommendation(
                    trend=trend,
                    relevance_score=relevance,
                    suggested_caption=await self._simple_caption(persona, trend),
                    suggested_hashtags=[trend.hashtag] if trend.hashtag else [],
                    content_type="caption" if trend.category != TrendCategory.CHALLENGE else "reel",
                    reasoning=f"Trend '{trend.title}' phù hợp {int(relevance*100)}% với persona",
                )
                recommendations.append(rec)

        return recommendations

    async def _ai_recommend(
        self,
        persona: Any,
        top_trends: list[tuple[Trend, float]],
    ) -> list[TrendRecommendation]:
        """Use LLM to generate detailed content recommendations."""
        trends_text = "\n".join(
            f"- [{t.source.value}] {t.title}: {t.description} (độ hot: {t.popularity_score:.0f})"
            for t, _ in top_trends
        )

        persona_context = f"""- Tên: {persona.name}
- Tuổi: {persona.age}
- Nghề: {persona.occupation}
- Sở thích: {', '.join(persona.interests)}
- Tính cách: {', '.join(persona.personality.get('traits', []))}
- Giọng điệu: {persona.personality.get('tone', 'tự nhiên')}"""

        system_prompt = TREND_ANALYSIS_SYSTEM.format(
            persona_name=persona.name,
            trends=trends_text,
            persona_context=persona_context,
        )

        try:
            result = await generate_json(
                system_prompt=system_prompt,
                user_prompt=f"Đề xuất {len(top_trends)} nội dung dựa trên trends cho {persona.name}. Trả về JSON array với format: [{{'trend_title': '...', 'caption': '...', 'hashtags': [...], 'content_type': 'caption|reel|story', 'reasoning': '...'}}]",
                temperature=0.7,
                use_lite=True,  # GPT-4o-mini cho trend recommendations
            )

            recommendations = []
            recs = result if isinstance(result, list) else result.get("recommendations", [])

            for i, rec in enumerate(recs):
                if i < len(top_trends):
                    trend, relevance = top_trends[i]
                    recommendations.append(
                        TrendRecommendation(
                            trend=trend,
                            relevance_score=relevance,
                            suggested_caption=rec.get("caption", ""),
                            suggested_hashtags=rec.get("hashtags", []),
                            content_type=rec.get("content_type", "caption"),
                            reasoning=rec.get("reasoning", ""),
                        )
                    )

            return recommendations

        except Exception:
            # Fallback to simple recommendations
            return []

    async def _simple_caption(self, persona: Any, trend: Trend) -> str:
        """Generate a simple caption suggestion without LLM."""
        templates = {
            TrendCategory.HASHTAG: f"Thấy mọi người đang bàn về #{trend.hashtag or trend.title} nhiều quá! Mình cũng muốn chia sẻ góc nhìn... {persona.personality.get('pet_phrases', [''])[0] if persona.personality.get('pet_phrases') else ''}",
            TrendCategory.CHALLENGE: f"Thử thách {trend.title} nè mọi người ơi! Ai dám thử cùng {persona.name} không?",
            TrendCategory.TOPIC: f"{trend.title} đang là chủ đề hot. Là {persona.occupation}, mình nghĩ...",
            TrendCategory.MEME: f"Cười xỉu với trend {trend.title} này 🤣",
            TrendCategory.NEWS: f"Đọc tin về {trend.title} mà suy nghĩ mãi... Mọi người thấy sao?",
            TrendCategory.SOUND: f"Sound {trend.title} đang viral quá! Để {persona.name} thử nha!",
        }
        return templates.get(trend.category, f"Trending: {trend.title}")
