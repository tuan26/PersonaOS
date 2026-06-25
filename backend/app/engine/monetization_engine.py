"""
Monetization Engine — Phase 7: turn a persona's audience into revenue.

Two AI capabilities:
1. suggest_products(persona)  → product/affiliate ideas that fit the persona's
   niche, interests and personality (so promotion feels natural & converts).
2. generate_promo(persona, product) → a promo caption in the persona's voice
   that weaves the product in authentically, with hashtags + a soft CTA.

Pure AI logic — no DB. Models (AffiliateProduct/ClickEvent/ConversionEvent)
are handled by MonetizationService.
"""

from __future__ import annotations

from typing import Any

from app.core.llm import generate_json


def _persona_context(persona: Any) -> str:
    traits = persona.personality.get("traits", []) if persona.personality else []
    return f"""- Tên: {persona.name}
- Tuổi: {persona.age}
- Nghề: {persona.occupation}
- Sở thích: {', '.join(persona.interests or []) or 'đa dạng'}
- Tính cách: {', '.join(traits) or 'đa dạng'}
- Giọng điệu: {persona.personality.get('tone', 'tự nhiên') if persona.personality else 'tự nhiên'}"""


class MonetizationEngine:
    """AI for product suggestions and promo content."""

    @staticmethod
    async def suggest_products(
        persona: Any,
        count: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Suggest affiliate/products that fit this persona's niche.
        Returns list of {name, category, why, sample_pitch}.
        """
        system_prompt = (
            "Bạn là chuyên gia affiliate marketing cho influencer. Đề xuất sản phẩm "
            "phù hợp NGÁCH của nhân vật để quảng bá tự nhiên, dễ chuyển đổi. "
            "Tránh sản phẩm lệch tông nhân vật. Trả về JSON."
        )
        user_prompt = f"""Nhân vật:
{_persona_context(persona)}

Đề xuất {count} sản phẩm/affiliate phù hợp để nhân vật này quảng bá.
Trả về JSON:
{{
  "suggestions": [
    {{
      "name": "Tên sản phẩm cụ thể",
      "category": "tech|beauty|fashion|travel|fitness|food|...",
      "why": "Vì sao hợp ngách nhân vật (1-2 câu)",
      "sample_pitch": "1 câu pitch ngắn theo giọng nhân vật"
    }}
  ]
}}
Sản phẩm phải CỤ THỂ, hợp sở thích & nghề của nhân vật, không generic."""

        result = await generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.8,
            use_lite=True,
        )
        return result if isinstance(result, list) else result.get("suggestions", [])

    @staticmethod
    async def generate_promo(
        persona: Any,
        product_name: str,
        product_category: str = "",
        affiliate_url: str = "",
        memories: list[Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a promo caption for a product in the persona's voice.
        Returns {caption, hashtags, cta}.
        """
        recent = ""
        if memories:
            recent = "\n".join(f"- {getattr(m, 'content', '')[:160]}" for m in memories[:3])

        system_prompt = (
            "Bạn viết bài quảng bá sản phẩm cho influencer sao cho TỰ NHIÊN, không "
            "lộ liễu 'quảng cáo', lồng ghép vào cuộc sống nhân vật, có lời kêu gọi "
            "nhẹ nhàng (CTA). Giữ đúng giọng điệu nhân vật. Trả về JSON."
        )
        user_prompt = f"""Nhân vật:
{_persona_context(persona)}
{f'Hoạt động gần đây:{chr(10)}{recent}' if recent else ''}

Sản phẩm cần quảng bá: {product_name} (danh mục: {product_category or 'chung'})

Viết 1 bài quảng bá tự nhiên theo giọng nhân vật. Trả về JSON:
{{
  "caption": "Nội dung bài đăng (lồng ghép sản phẩm tự nhiên, có cảm xúc)",
  "hashtags": ["hashtag1", "hashtag2", "..."],
  "cta": "Câu kêu gọi hành động ngắn"
}}"""

        result = await generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.85,
            use_lite=True,
        )
        result.setdefault("caption", "")
        result.setdefault("hashtags", [])
        result.setdefault("cta", "")
        if affiliate_url and result["cta"]:
            result["caption"] = f"{result['caption']}\n\n👉 {result['cta']}: {affiliate_url}"
        return result
