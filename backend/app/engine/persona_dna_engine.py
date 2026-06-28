"""
Persona DNA Engine — KOL Studio Phase 1: extract a brand-voice fingerprint
from a corpus of past posts.

Two layers:
1. Deterministic style metrics computed in Python (cheap, reliable):
   post length, words/sentence, emoji rate, hashtag rate, question/exclaim rate.
2. AI extraction (LLM) for the qualitative DNA: personality mix, signature
   phrases, post structure, tone, topics, do/don't.

Pure logic — no DB. Persistence handled by PersonaDNAService.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.llm import generate_json

# Rough emoji matcher (covers most common emoji blocks).
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F0FF←-⇿⬀-⯿]"
)
_SENT_SPLIT_RE = re.compile(r"[.!?…\n]+")
_HASHTAG_RE = re.compile(r"#\w+")

# Cost guard: cap how much corpus we send to the LLM.
_MAX_POSTS_FOR_LLM = 40
_MAX_CHARS_FOR_LLM = 14000


def _round(x: float, n: int = 1) -> float:
    return round(float(x), n)


def compute_style_metrics(posts: list[str]) -> dict[str, Any]:
    """Deterministic, language-agnostic style fingerprint."""
    clean = [p.strip() for p in posts if p and p.strip()]
    n = len(clean)
    if not n:
        return {}

    total_chars = sum(len(p) for p in clean)
    emoji_total = sum(len(_EMOJI_RE.findall(p)) for p in clean)
    hashtag_total = sum(len(_HASHTAG_RE.findall(p)) for p in clean)
    q_total = sum(p.count("?") for p in clean)
    ex_total = sum(p.count("!") for p in clean)

    words_per_sentence: list[float] = []
    for p in clean:
        sents = [s for s in _SENT_SPLIT_RE.split(p) if s.strip()]
        for s in sents:
            w = len(s.split())
            if w:
                words_per_sentence.append(w)
    avg_wps = sum(words_per_sentence) / len(words_per_sentence) if words_per_sentence else 0

    return {
        "post_count": n,
        "avg_post_chars": _round(total_chars / n, 0),
        "avg_words_per_sentence": _round(avg_wps, 1),
        "emoji_per_post": _round(emoji_total / n, 2),
        "hashtags_per_post": _round(hashtag_total / n, 2),
        "questions_per_post": _round(q_total / n, 2),
        "exclamations_per_post": _round(ex_total / n, 2),
    }


class PersonaDNAEngine:
    """Extracts brand DNA from a corpus of past posts."""

    @staticmethod
    async def analyze(posts: list[str], persona_name: str = "") -> dict[str, Any]:
        """
        Returns a dict with AI-extracted DNA fields + deterministic style_metrics.
        """
        clean = [p.strip() for p in posts if p and p.strip()]
        metrics = compute_style_metrics(clean)

        # Build a capped corpus sample for the LLM
        sample: list[str] = []
        chars = 0
        for p in clean[:_MAX_POSTS_FOR_LLM]:
            chars += len(p)
            if chars > _MAX_CHARS_FOR_LLM:
                break
            sample.append(p)

        corpus = "\n\n--- BÀI ---\n".join(sample)

        system_prompt = (
            "Bạn là chuyên gia phân tích thương hiệu cá nhân (personal brand). "
            "Nhiệm vụ: đọc kho bài đăng cũ của một KOL và trích ra 'DNA văn phong' "
            "— phong cách viết đặc trưng để AI có thể viết LẠI đúng giọng người đó. "
            "Phân tích khách quan, dựa trên bằng chứng trong bài. Trả về JSON."
        )
        user_prompt = f"""KOL: {persona_name or '(không tên)'}
Số bài phân tích: {len(sample)}

KHO BÀI ĐĂNG:
{corpus}

Trích DNA văn phong. Trả về JSON đúng cấu trúc:
{{
  "personality_mix": [{{"trait": "hài hước", "percent": 70}}, {{"trait": "chuyên gia", "percent": 20}}, {{"trait": "drama", "percent": 10}}],
  "signature_phrases": ["cụm từ/đặc ngữ hay lặp lại", "..."],
  "post_structure": {{"pattern": "VD: Hook → Story → CTA", "notes": "mô tả cách mở bài, triển khai, chốt"}},
  "topics": ["chủ đề thường viết", "..."],
  "tone": "mô tả giọng điệu tổng thể trong 1 câu",
  "voice_summary": "2-3 câu mô tả văn phong để người khác hiểu ngay",
  "dos": ["nên làm gì để giữ đúng giọng", "..."],
  "donts": ["tránh gì kẻo phá thương hiệu cá nhân", "..."]
}}
- personality_mix: tổng các percent = 100.
- signature_phrases: chỉ lấy cụm THẬT SỰ xuất hiện/đặc trưng, tối đa 12.
- Viết bằng tiếng Việt."""

        try:
            result = await generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.4,
                use_lite=False,  # dùng model mạnh — đây là phần lõi
            )
        except Exception:
            result = {}

        if not isinstance(result, dict):
            result = {}

        result.setdefault("personality_mix", [])
        result.setdefault("signature_phrases", [])
        result.setdefault("post_structure", {})
        result.setdefault("topics", [])
        result.setdefault("tone", "")
        result.setdefault("voice_summary", "")
        result.setdefault("dos", [])
        result.setdefault("donts", [])
        result["style_metrics"] = metrics
        result["sample_excerpts"] = clean[:3]
        result["source_count"] = len(clean)
        result["voice_vector"] = await _voice_centroid(sample)
        return result


async def _voice_centroid(posts: list[str]) -> list[float]:
    """Average embedding of the sampled posts — the persona's voice fingerprint."""
    from app.core.vector_store import _embed

    if not posts:
        return []
    embs = await _embed(posts)
    if not embs:
        return []
    dim = len(embs[0])
    centroid = [0.0] * dim
    for e in embs:
        for i in range(dim):
            centroid[i] += e[i]
    n = len(embs)
    return [c / n for c in centroid]
