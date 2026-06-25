"""
Analytics Engine — the engagement feedback loop.

Turns "auto-generate content" into "auto-generate content that LEARNS".

It reads a persona's published posts + their engagement metrics, figures out
what actually works (which content types, which posting hours, which hashtags),
and emits recommendations the scheduler/content engine use to bias the next
round of generation.

Pure, stateless analysis over a list of ContentPost ORM objects — no DB, no LLM.
With little/no data it returns sensible baseline defaults so the loop never
blocks on a cold start.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

# Baseline content mix (%) used when there isn't enough data yet.
_BASELINE_MIX = {"caption": 40, "story": 25, "reel_caption": 25, "image": 10}
_BASELINE_TIMES = ["08:00", "12:00", "19:00"]
_MIN_POSTS_FOR_LEARNING = 5


def _engagement(post: Any) -> float:
    """
    A single engagement score for a post.
    Prefer the stored engagement_rate; otherwise derive from raw counts with
    light weighting (comments/shares are worth more than likes/views).
    """
    rate = getattr(post, "engagement_rate", 0.0) or 0.0
    if rate > 0:
        return float(rate)
    likes = getattr(post, "likes_count", 0) or 0
    comments = getattr(post, "comments_count", 0) or 0
    shares = getattr(post, "shares_count", 0) or 0
    views = getattr(post, "views_count", 0) or 0
    return likes * 1.0 + comments * 3.0 + shares * 5.0 + views * 0.05


class AnalyticsEngine:
    """Analyzes content performance and recommends what to post next."""

    @staticmethod
    def analyze(posts: list[Any]) -> dict[str, Any]:
        """
        Analyze a persona's posts and return a recommendation bundle:

        {
          "sample_size": int,
          "learning": bool,                # True if enough data to trust results
          "by_type":  {type: {count, avg_engagement, total_engagement}},
          "by_hour":  {hour: avg_engagement},
          "top_hashtags": [(tag, avg_engagement), ...],
          "recommended_mix": {type: percent},   # sums to ~100
          "best_times": ["HH:MM", ...],
          "insights": [str, ...],               # human-readable, for the dashboard
        }
        """
        scored = [(p, _engagement(p)) for p in posts]
        # Only learn from posts that actually went out and have signal
        engaged = [(p, e) for p, e in scored if e > 0]
        sample = len(engaged)
        learning = sample >= _MIN_POSTS_FOR_LEARNING

        # ── Per content_type ─────────────────────────────────────
        type_total: dict[str, float] = defaultdict(float)
        type_count: dict[str, int] = defaultdict(int)
        for p, e in engaged:
            ct = getattr(p, "content_type", "caption") or "caption"
            type_total[ct] += e
            type_count[ct] += 1

        by_type = {
            ct: {
                "count": type_count[ct],
                "avg_engagement": round(type_total[ct] / type_count[ct], 2),
                "total_engagement": round(type_total[ct], 2),
            }
            for ct in type_count
        }

        # ── Per posting hour ─────────────────────────────────────
        hour_total: dict[int, float] = defaultdict(float)
        hour_count: dict[int, int] = defaultdict(int)
        for p, e in engaged:
            ts = getattr(p, "published_at", None) or getattr(p, "created_at", None)
            if ts is not None and hasattr(ts, "hour"):
                hour_total[ts.hour] += e
                hour_count[ts.hour] += 1
        by_hour = {
            h: round(hour_total[h] / hour_count[h], 2) for h in hour_count
        }

        # ── Top hashtags ─────────────────────────────────────────
        tag_total: dict[str, float] = defaultdict(float)
        tag_count: dict[str, int] = defaultdict(int)
        for p, e in engaged:
            for tag in (getattr(p, "hashtags", []) or []):
                key = str(tag).lstrip("#").lower()
                tag_total[key] += e
                tag_count[key] += 1
        top_hashtags = sorted(
            ((t, round(tag_total[t] / tag_count[t], 2)) for t in tag_count),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        # ── Recommendations ──────────────────────────────────────
        recommended_mix = AnalyticsEngine._recommend_mix(by_type, learning)
        best_times = AnalyticsEngine._recommend_times(by_hour, learning)
        insights = AnalyticsEngine._insights(
            sample, learning, by_type, best_times, top_hashtags
        )

        return {
            "sample_size": sample,
            "learning": learning,
            "by_type": by_type,
            "by_hour": by_hour,
            "top_hashtags": top_hashtags,
            "recommended_mix": recommended_mix,
            "best_times": best_times,
            "insights": insights,
        }

    @staticmethod
    def _recommend_mix(
        by_type: dict[str, dict[str, Any]], learning: bool
    ) -> dict[str, int]:
        """Allocate the content mix proportionally to avg engagement per type."""
        if not learning or not by_type:
            return dict(_BASELINE_MIX)

        weights = {ct: max(0.01, v["avg_engagement"]) for ct, v in by_type.items()}
        total = sum(weights.values())
        mix = {ct: round(w / total * 100) for ct, w in weights.items()}

        # Keep a little exploration on types we haven't measured yet
        for ct in _BASELINE_MIX:
            mix.setdefault(ct, 5)

        # Normalize to ~100
        s = sum(mix.values())
        if s:
            mix = {ct: round(v / s * 100) for ct, v in mix.items()}
        return mix

    @staticmethod
    def _recommend_times(by_hour: dict[int, float], learning: bool) -> list[str]:
        """Pick the top engagement hours; fall back to baseline times."""
        if not learning or not by_hour:
            return list(_BASELINE_TIMES)
        top = sorted(by_hour.items(), key=lambda x: x[1], reverse=True)[:3]
        top.sort(key=lambda x: x[0])  # chronological
        return [f"{h:02d}:00" for h, _ in top]

    @staticmethod
    def _insights(
        sample: int,
        learning: bool,
        by_type: dict[str, dict[str, Any]],
        best_times: list[str],
        top_hashtags: list[tuple[str, float]],
    ) -> list[str]:
        out: list[str] = []
        if not learning:
            out.append(
                f"Chưa đủ dữ liệu để học (mới {sample} bài có tương tác, "
                f"cần ≥ {_MIN_POSTS_FOR_LEARNING}). Đang dùng cấu hình mặc định."
            )
            return out

        best_type = max(
            by_type.items(), key=lambda x: x[1]["avg_engagement"], default=None
        )
        if best_type:
            out.append(
                f"Định dạng hiệu quả nhất: '{best_type[0]}' "
                f"(tương tác TB {best_type[1]['avg_engagement']})."
            )
        if best_times:
            out.append(f"Khung giờ tốt nhất: {', '.join(best_times)}.")
        if top_hashtags:
            tags = ", ".join(f"#{t}" for t, _ in top_hashtags[:5])
            out.append(f"Hashtag ăn tương tác: {tags}.")
        return out
