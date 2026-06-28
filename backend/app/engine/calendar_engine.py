"""
Content Calendar Engine — KOL Studio Phase 3.

Builds a multi-day content plan that respects a funnel ratio
(knowledge / story / sales, default 70/20/10) instead of random posting.

Two steps:
1. Build the pillar sequence in Python so the ratio is exact and sales/story
   slots are spread out evenly (greedy), not clumped.
2. Ask the LLM to fill each slot with an on-brand idea (title / topic / hook),
   guided by the persona's DNA topics & voice when available.
"""

from __future__ import annotations

from typing import Any

from app.core.llm import generate_json

_PILLAR_VI = {
    "knowledge": "Kiến thức / chia sẻ giá trị",
    "story": "Hậu trường / cảm xúc / câu chuyện",
    "sales": "Bán hàng / kêu gọi hành động",
}


def build_pillar_sequence(days: int, k: int, s: int, sa: int) -> list[str]:
    """Greedy-spread pillars across `days` to match the k/s/sa percentage mix."""
    total = max(1, k + s + sa)
    targets = {"knowledge": k / total, "story": s / total, "sales": sa / total}
    placed = {"knowledge": 0, "story": 0, "sales": 0}
    seq: list[str] = []
    for i in range(days):
        # pick the pillar most "behind" its target so far
        best, best_gap = "knowledge", -1.0
        for p, t in targets.items():
            if t <= 0:
                continue
            expected = t * (i + 1)
            gap = expected - placed[p]
            if gap > best_gap:
                best, best_gap = p, gap
        seq.append(best)
        placed[best] += 1
    return seq


class CalendarEngine:
    @staticmethod
    async def generate_plan(
        persona: Any,
        pillars: list[str],
        dna: Any | None = None,
        topics_hint: str = "",
    ) -> list[dict[str, Any]]:
        """
        Fill each pillar slot with an idea. Returns a list aligned to `pillars`:
        [{day_index, pillar, title, topic, hook}, ...].
        """
        dna_topics = ""
        voice = ""
        if dna is not None:
            dna_topics = ", ".join(getattr(dna, "topics", []) or [])
            voice = getattr(dna, "voice_summary", "") or ""

        interests = ", ".join(getattr(persona, "interests", []) or [])
        slots_text = "\n".join(
            f"{i+1}. [{p}] {_PILLAR_VI.get(p, p)}" for i, p in enumerate(pillars)
        )

        system_prompt = (
            "Bạn là chiến lược gia nội dung cho KOL. Lên lịch nội dung đa dạng, "
            "không trùng lặp, bám đúng PILLAR mỗi ngày (knowledge/story/sales). "
            "Bài bán hàng phải tinh tế, lồng vào giá trị — KHÔNG spam. Trả về JSON."
        )
        user_prompt = f"""KOL: {persona.name} — {getattr(persona, 'occupation', '')}
Sở thích/ngách: {interests or '—'}
Chủ đề hay viết (từ DNA): {dna_topics or '—'}
Văn phong: {voice or '—'}
Định hướng thêm: {topics_hint or '—'}

Có {len(pillars)} ngày, mỗi ngày 1 PILLAR cố định (giữ nguyên thứ tự):
{slots_text}

Với MỖI ngày, nghĩ 1 ý tưởng nội dung CỤ THỂ, hợp ngách & đúng pillar.
Trả về JSON:
{{
  "items": [
    {{"day": 1, "title": "tiêu đề ngắn gọn", "topic": "mô tả nội dung 1 câu", "hook": "câu mở đầu gây chú ý"}},
    ...
  ]
}}
- Đúng {len(pillars)} mục, theo thứ tự ngày.
- Đa dạng, không lặp ý. Viết tiếng Việt."""

        try:
            result = await generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8,
                use_lite=False,
            )
        except Exception:
            result = {}

        items = []
        if isinstance(result, dict):
            items = result.get("items") or next(
                (v for v in result.values() if isinstance(v, list)), []
            )
        elif isinstance(result, list):
            items = result

        out: list[dict[str, Any]] = []
        for i, pillar in enumerate(pillars):
            it = items[i] if i < len(items) and isinstance(items[i], dict) else {}
            out.append({
                "day_index": i,
                "pillar": pillar,
                "title": (it.get("title") or "").strip(),
                "topic": (it.get("topic") or "").strip(),
                "hook": (it.get("hook") or "").strip(),
            })
        return out
