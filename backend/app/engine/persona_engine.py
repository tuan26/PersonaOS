"""
Persona Engine — Phase 1: Generate AI Influencer personas with depth.

This engine uses LLM to create a "digital human" with:
- Identity (name, age, occupation)
- Personality (traits, tone, quirks, fears)
- Backstory (life narrative)
- Goals and dreams
"""

from __future__ import annotations

from typing import Any

from app.core.llm import generate_json
from app.utils.prompt_templates import (
    PERSONA_GENERATION_SYSTEM,
    PERSONA_GENERATION_USER,
)


class PersonaEngine:
    """
    Generates complete persona profiles using AI.

    Usage:
        engine = PersonaEngine()
        persona_data = await engine.generate(
            concept="Dev IT nữ 25t thích Nhật Bản, nuôi mèo"
        )
    """

    @staticmethod
    async def generate(
        concept: str = "",
        gender: str | None = None,
        age_range: str | None = None,
        occupation_hint: str | None = None,
        interests_hint: str | None = None,
        location: str = "Việt Nam",
        language: str = "vi",
        appearance_hint: str = "",
        voice_hint: str = "",
        fashion_hint: str = "",
        creativity: float = 0.8,
        # ── User-specified concrete values ──
        name_override: str = "",
        nickname_override: str = "",
        age_value: int | None = None,
        occupation_override: str = "",
        looks_like: str = "",
        unique_appeal_override: str = "",
        personality_type_override: str = "",
    ) -> dict[str, Any]:
        """
        Generate a complete persona profile.

        Args with OVERRIDE suffix are USER-SPECIFIED values that AI MUST use exactly.
        """
        # Build the appearance/identity overrides section
        identity_override = ""
        if name_override or nickname_override or age_value or occupation_override:
            identity_override = "\n\n⚠️ THÔNG TIN BẮT BUỘC (phải dùng CHÍNH XÁC, không được thay đổi):"
            if name_override:
                identity_override += f"\n- TÊN: {name_override} (DÙNG CHÍNH XÁC TÊN NÀY)"
            if nickname_override:
                identity_override += f"\n- BIỆT DANH: {nickname_override} (DÙNG CHÍNH XÁC)"
            if age_value:
                identity_override += f"\n- TUỔI: {age_value} (DÙNG CHÍNH XÁC)"
            if occupation_override:
                identity_override += f"\n- NGHỀ NGHIỆP: {occupation_override} (DÙNG CHÍNH XÁC)"
            if looks_like:
                identity_override += f"\n- NGOẠI HÌNH GIỐNG: {looks_like} (phải để trong trường looks_like)"
            if unique_appeal_override:
                identity_override += f"\n- ĐIỂM THU HÚT: {unique_appeal_override} (dùng chính xác)"
            if personality_type_override:
                identity_override += f"\n- TÍNH CÁCH: {personality_type_override} (dùng chính xác)"

        user_prompt = PERSONA_GENERATION_USER.format(
            concept=concept or "Tự do sáng tạo một nhân vật thú vị, có chiều sâu",
            gender=gender or "Tự do",
            age_range=age_range or str(age_value) if age_value else "Tự do (18-40)",
            occupation_hint=occupation_override or occupation_hint or "Tự do chọn nghề nghiệp phù hợp",
            interests_hint=interests_hint or "Tự do chọn sở thích đa dạng",
            location=location,
            language=language,
            appearance_hint=appearance_hint or "Tự do sáng tạo",
            voice_hint=voice_hint or "Tự do",
            fashion_hint=fashion_hint or "Tự do chọn phong cách phù hợp với nghề nghiệp và tính cách",
        ) + identity_override

        result = await generate_json(
            system_prompt=PERSONA_GENERATION_SYSTEM,
            user_prompt=user_prompt,
            temperature=creativity,
        )

        # Ensure required fields exist with defaults
        result.setdefault("gender", "nữ")
        result.setdefault("location", location)
        result.setdefault("bio", "")
        result.setdefault("backstory", "")
        result.setdefault("life_goals", [])
        result.setdefault("interests", [])

        personality = result.get("personality", {})
        personality.setdefault("traits", [])
        personality.setdefault("tone", "thân thiện, tự nhiên")
        personality.setdefault("speaking_style", "tự nhiên, có dùng emoji")
        personality.setdefault("values", [])
        personality.setdefault("quirks", [])
        personality.setdefault("fears", [])
        personality.setdefault("pet_phrases", [])
        result["personality"] = personality

        # Store generation metadata
        result["generation_meta"] = {
            "concept": concept,
            "creativity": creativity,
            "language": language,
        }

        return result

    @staticmethod
    def to_persona_dict(generated: dict[str, Any]) -> dict[str, Any]:
        """
        Convert generated persona data to DB-ready dict.
        Includes: nickname, concept_description, fashion_style, unique_appeal, avatar_gen_prompt.
        """
        personality = generated.get("personality", {})
        appearance = generated.get("appearance", {})

        return {
            "name": generated["name"],
            "nickname": generated.get("nickname", ""),
            "age": generated["age"],
            "gender": generated.get("gender", "nữ"),
            "occupation": generated["occupation"],
            "location": generated.get("location", "Việt Nam"),
            "bio": generated.get("bio", ""),
            # ── NEW: Concept & Avatar ──
            "concept_description": generated.get("concept_description", ""),
            "avatar_gen_prompt": generated.get("avatar_gen_prompt", ""),
            # ── Appearance ──
            "appearance": {
                "description": appearance.get("description", ""),
                "style": appearance.get("style", ""),
                "looks_like": appearance.get("looks_like", ""),
                "height": appearance.get("height", ""),
                "body_type": appearance.get("body_type", ""),
                "reference_images": appearance.get("reference_images", []),
            },
            "fashion_style": generated.get("fashion_style", ""),
            "unique_appeal": generated.get("unique_appeal", ""),
            "voice_style": generated.get("voice_style", "tự nhiên"),
            "personality_type": generated.get("personality_type", "ambivert"),
            # ── Existing ──
            "personality": personality,
            "interests": generated.get("interests", []),
            "life_goals": generated.get("life_goals", []),
            "relationships": generated.get("relationships", []),
            "backstory": generated.get("backstory", ""),
            "generation_prompt": generated.get("generation_meta", {}).get("concept", ""),
        }
