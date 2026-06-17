"""
Media Service — Upload & generate images for personas.

Handles:
- Image upload (reference images, avatars)
- AI avatar generation via DALL-E
- Image storage management
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.llm import get_openai_client


class MediaService:
    """Manages image uploads and AI-generated avatar images."""

    UPLOAD_DIR = settings.MEDIA_DIR
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

    @classmethod
    def init_dirs(cls):
        """Ensure media directories exist."""
        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        (cls.UPLOAD_DIR / "avatars").mkdir(parents=True, exist_ok=True)
        (cls.UPLOAD_DIR / "reference").mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_upload_path(cls, subfolder: str, filename: str) -> Path:
        """Get full path for an uploaded file."""
        cls.init_dirs()
        return cls.UPLOAD_DIR / subfolder / filename

    @classmethod
    def get_url(cls, subfolder: str, filename: str) -> str:
        """Get the URL for accessing a stored image."""
        return f"/media/{subfolder}/{filename}"

    # ── Upload ───────────────────────────────────────────────────

    @classmethod
    async def save_upload(
        cls,
        file_data: bytes,
        original_filename: str,
        subfolder: str = "reference",
    ) -> dict[str, Any]:
        """
        Save an uploaded image file.

        Returns dict with: filename, path, url, size
        """
        cls.init_dirs()

        # Generate unique filename
        ext = Path(original_filename).suffix.lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Định dạng không hỗ trợ: {ext}. Hỗ trợ: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            )

        unique_name = f"{uuid.uuid4().hex}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{ext}"
        file_path = cls.get_upload_path(subfolder, unique_name)

        # Save file
        file_path.write_bytes(file_data)

        return {
            "filename": unique_name,
            "original_name": original_filename,
            "path": str(file_path),
            "url": cls.get_url(subfolder, unique_name),
            "size": len(file_data),
        }

    # ── Avatar Generation (DALL-E) ────────────────────────────────

    @classmethod
    async def generate_avatar(
        cls,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        persona_name: str = "",
        persona_gender: str = "",
        persona_age: str = "",
        persona_style: str = "",
    ) -> dict[str, Any]:
        """
        Generate an avatar image.

        Strategy:
        1. GPT Image models (gpt-image-1, gpt-image-2) — OpenAI mới
        2. DALL-E 3 / DALL-E 2 (legacy, nếu API key có quyền)
        3. DiceBear SVG (luôn hoạt động, miễn phí)
        """
        import logging
        import hashlib
        import base64

        # ── 1. Try GPT Image models (OpenAI mới) ─────────────────
        for img_model in ["gpt-image-1.5", "gpt-image-2", "gpt-image-1", "gpt-image-1-mini"]:
            try:
                client = get_openai_client()
                response = await client.images.generate(
                    model=img_model,
                    prompt=prompt[:4000],
                    n=1,
                    size=size if img_model in ("gpt-image-1", "gpt-image-2") else "1024x1024",
                )
                image_data = response.data[0]
                revised_prompt = getattr(image_data, 'revised_prompt', prompt)

                # GPT Image models return b64_json instead of url
                if getattr(image_data, 'b64_json', None):
                    img_bytes = base64.b64decode(image_data.b64_json)
                    saved = await cls.save_upload(
                        file_data=img_bytes,
                        original_filename=f"avatar_{uuid.uuid4().hex[:8]}.png",
                        subfolder="avatars",
                    )
                    return {"url": saved["url"], "local_path": saved["path"], "revised_prompt": revised_prompt, "source": img_model}

                # Fallback: traditional url
                image_url = image_data.url
                if image_url:
                    import httpx
                    async with httpx.AsyncClient() as http:
                        img_resp = await http.get(image_url)
                        if img_resp.status_code == 200:
                            saved = await cls.save_upload(
                                file_data=img_resp.content,
                                original_filename=f"avatar_{uuid.uuid4().hex[:8]}.png",
                                subfolder="avatars",
                            )
                            return {"url": saved["url"], "local_path": saved["path"], "revised_prompt": revised_prompt, "source_url": image_url, "source": img_model}
                    return {"url": image_url, "revised_prompt": revised_prompt, "source_url": image_url, "source": img_model}
            except Exception as e:
                err_msg = str(e)[:100]
                logging.warning(f"{img_model} unavailable: {err_msg}")
                if "401" in err_msg or "403" in err_msg:
                    break
                continue

        # ── 2. Try legacy DALL-E ─────────────────────────────────
        for dalle_model in ["dall-e-3", "dall-e-2"]:
            try:
                client = get_openai_client()
                img_size = size if dalle_model == "dall-e-3" else "512x512"
                response = await client.images.generate(
                    model=dalle_model,
                    prompt=prompt[:4000],
                    size=img_size,
                    quality=quality if dalle_model == "dall-e-3" else "standard",
                    n=1,
                )
                image_url = response.data[0].url
                revised_prompt = response.data[0].revised_prompt

                import httpx
                async with httpx.AsyncClient() as http:
                    img_resp = await http.get(image_url)
                    if img_resp.status_code == 200:
                        saved = await cls.save_upload(
                            file_data=img_resp.content,
                            original_filename=f"avatar_{uuid.uuid4().hex[:8]}.png",
                            subfolder="avatars",
                        )
                        return {"url": saved["url"], "local_path": saved["path"], "revised_prompt": revised_prompt, "source_url": image_url, "source": dalle_model}

                return {"url": image_url, "revised_prompt": revised_prompt, "source_url": image_url, "source": dalle_model}
            except Exception as e:
                logging.warning(f"{dalle_model} unavailable: {str(e)[:80]}")
                continue

        # ── 3. DiceBear với thông tin cá nhân hóa ────────────────
        seed_str = f"{persona_name}_{persona_gender}_{persona_age}_{prompt[:50]}"
        seed = hashlib.md5(seed_str.encode()).hexdigest()

        # Map giới tính để DiceBear
        gender_param = "female" if "nữ" in persona_gender.lower() else "male" if "nam" in persona_gender.lower() else "neutral"

        # Style dựa trên persona_style
        style_opts = {
            "cute": "avataaars",
            "professional": "avataaars",
            "elegant": "avataaars",
            "casual": "avataaars",
            "sporty": "avataaars",
        }
        dicebear_style = style_opts.get(persona_style.lower(), "avataaars")

        avatar_url = f"https://api.dicebear.com/9.x/{dicebear_style}/svg?seed={seed}&gender={gender_param}"
        logging.info(f"DiceBear avatar: {avatar_url[:80]}...")
        return {"url": avatar_url, "revised_prompt": prompt, "source_url": avatar_url, "source": "dicebear", "note": "API key không có quyền tạo ảnh. Avatar từ DiceBear (SVG)."}

    @classmethod
    async def generate_avatar_lite(cls, prompt: str) -> dict[str, Any]:
        """Generate avatar using DiceBear (free)."""
        import hashlib
        seed = hashlib.md5(prompt.encode()).hexdigest()
        return {"url": f"https://api.dicebear.com/9.x/avataaars/svg?seed={seed}", "source": "dicebear"}
