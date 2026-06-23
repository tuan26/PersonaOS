"""
Persona Service — CRUD + AI generation for personas.

Orchestrates PersonaEngine + Database operations.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.persona_engine import PersonaEngine
from app.core.llm import generate_text
from app.models.persona import Persona
from app.schemas.persona import PersonaCreate, PersonaGenerateRequest, PersonaUpdate


class PersonaService:
    """Manages persona lifecycle: create, generate, update, delete, list."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── AI Generation ────────────────────────────────────────────

    async def generate(self, request: PersonaGenerateRequest) -> Persona:
        """
        Use AI to generate a complete persona, then persist it.

        This is the core of Phase 1: Persona Engine.
        """
        from app.config import settings

        # ── Validate API key ─────────────────────────────────────
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-your-"):
            raise ValueError(
                "⚠️ Chưa cấu hình OpenAI API Key! Vào file .env, sửa OPENAI_API_KEY=sk-... bằng key thật của bạn. "
                "Lấy key tại: https://platform.openai.com/api-keys"
            )

        # ── Vision Analysis on Reference Image ────────────────────
        ref_image_prompt_en = ""
        ref_image_desc_vi = ""
        if request.reference_image_urls:
            try:
                from app.services.media_service import MediaService
                first_ref = request.reference_image_urls[0]
                analysis = await MediaService.analyze_reference_image(first_ref)
                ref_image_prompt_en = analysis.get("prompt_en", "")
                ref_image_desc_vi = analysis.get("description_vi", "")
                
                # Update appearance hint for PersonaEngine
                if ref_image_desc_vi:
                    if request.appearance_hint:
                        request.appearance_hint = f"{request.appearance_hint}. Ngoại hình thực tế: {ref_image_desc_vi}"
                    else:
                        request.appearance_hint = ref_image_desc_vi
            except Exception as e:
                import logging
                logging.warning(f"Không thể phân tích ảnh tham chiếu bằng Vision: {e}")

        # 1. Generate persona data via LLM
        generated = await PersonaEngine.generate(
            concept=request.concept,
            gender=request.gender,
            age_range=request.age_range,
            occupation_hint=request.occupation_hint,
            interests_hint=request.interests_hint,
            location=request.location,
            language=request.language,
            appearance_hint=request.appearance_hint or "",
            voice_hint=request.voice_hint or "",
            fashion_hint=request.fashion_hint or "",
            creativity=request.creativity,
            # ── User-specified concrete values ──
            name_override=request.name or "",
            nickname_override=request.nickname or "",
            age_value=request.age,
            occupation_override=request.occupation or "",
            looks_like=getattr(request, 'looks_like', '') or "",
            unique_appeal_override=getattr(request, 'unique_appeal', '') or "",
            personality_type_override=getattr(request, 'personality_type', '') or "",
        )

        # 2. Convert to DB-ready dict
        persona_dict = PersonaEngine.to_persona_dict(generated)

        # Use the DALL-E prompt analyzed from reference image if available
        if ref_image_prompt_en:
            persona_dict["avatar_gen_prompt"] = ref_image_prompt_en

        # 2b. Merge uploaded reference images
        if request.reference_image_urls:
            existing_refs = persona_dict.get("appearance", {}).get("reference_images", [])
            persona_dict.setdefault("appearance", {})
            persona_dict["appearance"]["reference_images"] = existing_refs + request.reference_image_urls

        # 3. Create and persist
        persona = Persona(**persona_dict)
        self.db.add(persona)
        await self.db.flush()
        await self.db.refresh(persona)

        # 4. Auto-generate avatar if avatar_gen_prompt exists
        if persona.avatar_gen_prompt:
            try:
                from app.services.media_service import MediaService
                avatar_result = await MediaService.generate_avatar(
                    prompt=persona.avatar_gen_prompt,
                    size="1024x1024",
                    quality="standard",
                    persona_name=persona.name or "",
                    persona_gender=persona.gender or "",
                    persona_age=str(persona.age or ""),
                    persona_style=(persona.interests or [""])[0] if persona.interests else "",
                )
                persona.avatar_url = avatar_result.get("url", "")
                await self.db.flush()
                await self.db.refresh(persona)
            except Exception as e:
                import logging
                logging.warning(f"Avatar generation failed for {persona.name}: {e}")

        return persona

    # ── CRUD ─────────────────────────────────────────────────────

    async def create(self, data: PersonaCreate) -> Persona:
        """Manually create a persona (without AI generation)."""
        persona = Persona(**data.model_dump())
        self.db.add(persona)
        await self.db.flush()
        await self.db.refresh(persona)
        return persona

    async def get(self, persona_id: str) -> Persona | None:
        """Get a persona by ID."""
        result = await self.db.execute(
            select(Persona).where(Persona.id == persona_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Persona]:
        """List personas with optional filters."""
        stmt = select(Persona)

        if is_active is not None:
            stmt = stmt.where(Persona.is_active == is_active)

        stmt = stmt.order_by(Persona.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, persona_id: str, data: PersonaUpdate) -> Persona | None:
        """Update a persona's fields."""
        persona = await self.get(persona_id)
        if not persona:
            return None

        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        for key, value in update_data.items():
            setattr(persona, key, value)

        await self.db.flush()
        await self.db.refresh(persona)
        return persona

    async def delete(self, persona_id: str) -> bool:
        """Soft-delete (deactivate) a persona."""
        persona = await self.get(persona_id)
        if not persona:
            return False
        persona.is_active = False
        await self.db.flush()
        return True

    async def hard_delete(self, persona_id: str) -> bool:
        """Permanently delete a persona and all related data."""
        persona = await self.get(persona_id)
        if not persona:
            return False
        await self.db.delete(persona)
        await self.db.flush()
        return True

    async def count(self) -> int:
        """Count total personas."""
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).select_from(Persona)
        )
        return result.scalar() or 0

    # ── Regenerate ───────────────────────────────────────────────

    async def regenerate_field(
        self,
        persona: Persona,
        field: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Regenerate a single field of a persona using AI.
        Returns dict with the regenerated field value.
        """
        ctx = context or {}
        concept = ctx.get("concept") or persona.concept_description or ""
        current_value = getattr(persona, field, "") or ""

        from app.engine.persona_engine import PersonaEngine

        # Build regeneration prompt for one field
        prompt = f"""Bạn đang tạo nhân vật: {concept}

Thông tin hiện tại:
- Tên: {persona.name}
- Tuổi: {persona.age}
- Nghề: {persona.occupation}
- Giới tính: {persona.gender}
- Sở thích: {', '.join(persona.interests or [])}"""

        field_prompts = {
            "name": "Hãy đề xuất một cái tên VIỆT NAM mới cho nhân vật này, phù hợp với concept và độ tuổi. Chỉ trả về tên.",
            "nickname": "Hãy đề xuất một biệt danh mới cho nhân vật này, thường là tên tiếng Anh hoặc biệt danh thân mật. Chỉ trả về biệt danh.",
            "age": "Hãy đề xuất độ tuổi phù hợp cho nhân vật này. Chỉ trả về số.",
            "occupation": "Hãy đề xuất một nghề nghiệp mới phù hợp với concept của nhân vật. Chỉ trả về tên nghề.",
            "fashion_style": f"Mô tả phong cách thời trang CHI TIẾT cho nhân vật (3-5 câu tiếng Việt). Current: {str(current_value)[:200]}. Hãy sáng tạo hơn! Chỉ trả về text.",
            "unique_appeal": f"Mô tả điểm thu hút đặc biệt của nhân vật - điều gì làm người ta nhớ mãi (2-3 câu tiếng Việt). Current: {str(current_value)[:200]}. Hay hơn nữa! Chỉ trả về text.",
            "appearance": f"Mô tả ngoại hình CHI TIẾT cho nhân vật (4-6 câu tiếng Việt: mặt, tóc, mắt, dáng, da...). Current: {str(current_value)[:300]}. Hãy miêu tả sống động! Chỉ trả về text.",
            "voice_style": f"Mô tả giọng nói của nhân vật (1-2 câu: chất giọng, cách nói, cảm xúc khi nói). Current: {str(current_value)[:100]}. Chỉ trả về text.",
            "personality_type": "Xác định kiểu tính cách: introvert, extrovert, hay ambivert? Chỉ trả về MỘT từ.",
            "interests": "Đề xuất 5-7 sở thích mới cho nhân vật, cách nhau dấu phẩy (VD: du lịch, chụp ảnh, đọc sách, gym, cafe). Chỉ trả về danh sách.",
            "life_goals": f"Hãy tạo 3 mục tiêu cuộc đời cho nhân vật. Trả về JSON array: [{{\"goal\":\"...\", \"progress\": 0, \"category\": \"...\", \"status\": \"planning\"}}, ...]. Current: {str(current_value)[:200]}",
            "relationships": f"Hãy tạo 2-3 mối quan hệ cho nhân vật. Trả về JSON array: [{{\"name\":\"...\", \"type\":\"friend|pet|family|mentor\", \"description\":\"...\", \"status\": \"...\", \"since\": \"2024\"}}, ...]. Current: {str(current_value)[:200]}",
        }

        user_msg = field_prompts.get(field, f"Hãy tạo mới field '{field}' cho nhân vật này.")

        # For JSON fields, use generate_json instead of generate_text
        if field in ("life_goals", "relationships"):
            import json as _json
            from app.core.llm import generate_json as _gen_json
            try:
                json_result = await _gen_json(
                    system_prompt=prompt,
                    user_prompt=user_msg,
                    temperature=0.85,
                )
                return {field: json_result if isinstance(json_result, list) else _json.loads(json_result)}
            except Exception:
                pass  # fall through to text generation

        result_text = await generate_text(
            system_prompt=prompt,
            user_prompt=user_msg,
            temperature=0.85,
            use_lite=True,
        )

        result_text = result_text.strip().strip('"').strip("'").strip('"')
        return {field: result_text}

    async def regenerate_avatar(self, persona: Persona, reference_image_url: Optional[str] = None) -> str:
        """Regenerate avatar using AI, return URL."""
        from app.services.media_service import MediaService

        # ── Phân tích ảnh tham chiếu mới bằng Vision nếu có ──
        if reference_image_url:
            try:
                analysis = await MediaService.analyze_reference_image(reference_image_url)
                prompt_en = analysis.get("prompt_en")
                desc_vi = analysis.get("description_vi")

                if prompt_en:
                    persona.avatar_gen_prompt = prompt_en

                # Cập nhật thông tin ngoại hình
                app_data = dict(persona.appearance or {})
                if desc_vi:
                    app_data["description"] = desc_vi

                # Thêm ảnh tham chiếu mới vào danh sách
                refs = app_data.get("reference_images", [])
                if reference_image_url not in refs:
                    refs.append(reference_image_url)
                app_data["reference_images"] = refs

                persona.appearance = app_data
            except Exception as e:
                import logging
                logging.warning(f"Lỗi phân tích ảnh tham chiếu mới trong regenerate_avatar: {e}")

        prompt = persona.avatar_gen_prompt or f"Portrait of a {persona.age}-year-old Vietnamese {persona.gender or 'person'}, {persona.occupation or 'modern professional'}, fashion style"

        result = await MediaService.generate_avatar(
            prompt=prompt,
            persona_name=persona.name,
            persona_gender=persona.gender or "",
            persona_age=str(persona.age or ""),
            persona_style=(persona.interests or [""])[0] if persona.interests else "",
        )
        url = result.get("url", "")

        persona.avatar_url = url
        await self.db.flush()
        await self.db.refresh(persona)
        return url
