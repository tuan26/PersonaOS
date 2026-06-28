"""
Voice Engine — KOL Studio Phase 2: write in the KOL's voice + score similarity.

Uses the Persona DNA (Phase 1) to:
1. generate_in_voice() — write a post on a topic in the KOL's exact style
   (personality mix, signature phrases, structure, tone, length/emoji habits).
2. score_voice_match() — estimate how close a draft is to the KOL's voice,
   blending: semantic similarity (embedding vs voice centroid), style-metric
   closeness, and signature-phrase usage. Returns a transparent breakdown.

The score is an *estimate* ("điểm tương đồng phong cách"), shown with its parts.
"""

from __future__ import annotations

import math
from typing import Any

from app.core.llm import generate_json
from app.engine.persona_dna_engine import compute_style_metrics


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# Metrics used for style-closeness and a rough "natural scale" for each,
# so an absolute difference is normalized into 0..1.
_STYLE_KEYS = {
    "avg_post_chars": 200.0,
    "avg_words_per_sentence": 10.0,
    "emoji_per_post": 3.0,
    "hashtags_per_post": 4.0,
    "questions_per_post": 2.0,
    "exclamations_per_post": 2.0,
}


def _style_closeness(draft_metrics: dict[str, Any], dna_metrics: dict[str, Any]) -> float:
    if not dna_metrics:
        return 0.0
    sims = []
    for k, scale in _STYLE_KEYS.items():
        a = float(draft_metrics.get(k, 0) or 0)
        b = float(dna_metrics.get(k, 0) or 0)
        sims.append(1.0 - min(1.0, abs(a - b) / scale))
    return sum(sims) / len(sims) if sims else 0.0


def _phrase_usage(text: str, phrases: list[str]) -> tuple[float, list[str]]:
    if not phrases:
        return 0.0, []
    low = text.lower()
    used = [p for p in phrases if p and p.lower() in low]
    target = min(3, len(phrases))  # using ~3 signature phrases is plenty
    return _clamp01(len(used) / target), used


class VoiceEngine:
    """Generate-in-voice and score-against-voice."""

    @staticmethod
    async def generate_in_voice(
        persona: Any,
        dna: Any,
        topic: str,
        content_type: str = "post",
    ) -> dict[str, Any]:
        """Write a post about `topic` in the KOL's voice, guided by the DNA."""
        mix = ", ".join(
            f"{m.get('trait')} {m.get('percent')}%" for m in (dna.personality_mix or [])
        ) or "tự nhiên"
        phrases = ", ".join(dna.signature_phrases or []) or "(không có)"
        struct = (dna.post_structure or {}).get("pattern", "Hook → Story → CTA")
        sm = dna.style_metrics or {}
        emoji_hint = sm.get("emoji_per_post", 1)
        len_hint = sm.get("avg_post_chars", 200)

        system_prompt = (
            "Bạn là chính KOL này đang tự viết bài. Viết Y HỆT văn phong của họ "
            "dựa trên DNA cung cấp — KHÔNG viết giọng AI chung chung. Giữ đúng "
            "tỷ lệ tính cách, dùng đặc ngữ tự nhiên (không nhồi nhét), bám cấu "
            "trúc bài và độ dài/emoji quen thuộc. Trả về JSON."
        )
        user_prompt = f"""DNA VĂN PHONG của {persona.name}:
- Tỷ lệ tính cách: {mix}
- Đặc ngữ hay dùng: {phrases}
- Cấu trúc bài: {struct}
- Giọng điệu: {dna.tone or 'tự nhiên'}
- Tóm tắt văn phong: {dna.voice_summary or ''}
- Thói quen: ~{len_hint} ký tự/bài, ~{emoji_hint} emoji/bài
- Nên: {', '.join(dna.dos or []) or '—'}
- Tránh: {', '.join(dna.donts or []) or '—'}

CHỦ ĐỀ cần viết: {topic}
Loại nội dung: {content_type}

Viết 1 bài đúng giọng KOL này. Trả về JSON:
{{
  "caption": "nội dung bài (đúng văn phong, đúng cấu trúc)",
  "hashtags": ["...", "..."]
}}"""

        try:
            result = await generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.85,
                use_lite=False,
            )
        except Exception:
            result = {}
        if not isinstance(result, dict):
            result = {}
        result.setdefault("caption", "")
        result.setdefault("hashtags", [])
        return result

    @staticmethod
    async def score_voice_match(text: str, dna: Any) -> dict[str, Any]:
        """
        Estimate how close `text` is to the KOL's voice. Returns:
        {match_percent, semantic, style, phrase, used_phrases, has_vector}.
        """
        from app.core.vector_store import _embed

        # 1. Semantic similarity vs voice centroid
        semantic = 0.0
        has_vector = bool(dna.voice_vector)
        if has_vector:
            embs = await _embed([text])
            if embs:
                cos = _cosine(embs[0], dna.voice_vector)
                # Map cosine → 0..1: 0.20 ≈ unrelated, 0.75 ≈ very on-voice.
                semantic = _clamp01((cos - 0.20) / (0.75 - 0.20))

        # 2. Style-metric closeness
        style = _style_closeness(compute_style_metrics([text]), dna.style_metrics or {})

        # 3. Signature-phrase usage
        phrase, used = _phrase_usage(text, dna.signature_phrases or [])

        # Blend. If no voice vector, reweight onto style+phrase.
        if has_vector:
            blended = 0.55 * semantic + 0.30 * style + 0.15 * phrase
        else:
            blended = 0.70 * style + 0.30 * phrase

        return {
            "match_percent": round(blended * 100),
            "semantic": round(semantic * 100),
            "style": round(style * 100),
            "phrase": round(phrase * 100),
            "used_phrases": used,
            "has_vector": has_vector,
        }
