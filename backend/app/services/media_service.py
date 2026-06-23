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

    @classmethod
    async def analyze_reference_image(cls, image_url: str) -> dict[str, str]:
        """
        Phân tích ảnh tham chiếu bằng GPT-4o Vision để viết prompt DALL-E 3
        và mô tả tiếng Việt đồng bộ với ngoại hình.
        """
        import base64
        import mimetypes
        import json
        import logging
        from app.core.llm import get_openai_client

        try:
            # 1. Lấy tên file từ URL (ví dụ: /media/reference/filename.ext)
            filename = image_url.split("/")[-1]
            file_path = cls.get_upload_path("reference", filename)

            if not file_path.exists():
                logging.warning(f"Không tìm thấy file ảnh tham chiếu tại {file_path}")
                return {"prompt_en": "", "description_vi": ""}

            # 2. Đọc file ảnh và mã hóa base64
            image_bytes = file_path.read_bytes()
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            # Xác định mime type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                mime_type = "image/png"

            # 3. Gọi GPT-4o Vision để phân tích
            client = get_openai_client()

            system_prompt = (
                "You are an expert AI Influencer designer. Analyze the uploaded reference image "
                "and output a JSON object containing:\n"
                "1. 'prompt_en': A highly detailed, professional prompt in English to generate a highly similar portrait "
                "using OpenAI gpt-image-2 model. Include details like: portrait shot, approximate age, gender (must match the person in the image), "
                "facial features, expression, hairstyle, lighting (e.g. soft studio lighting), clothing style, background, "
                "and camera style (e.g., 85mm lens, depth of field, photorealistic, fashion photography). DO NOT mention "
                "names of specific real people. Focus on visual description. The prompt should be very long and detailed (at least 500 words).\n"
                "2. 'description_vi': A detailed description of this person's appearance in Vietnamese (about 4-6 sentences) "
                "describing hair, face, expression, clothing style, style of photo.\n"
                "Ensure the output is valid JSON format like: {\"prompt_en\": \"...\", \"description_vi\": \"...\"}."
            )

            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,  # gpt-4o
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Hãy phân tích bức ảnh này để tạo prompt sinh ảnh tương tự và mô tả ngoại hình nhân vật."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
                max_tokens=1000
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as e:
            logging.error(f"Lỗi khi phân tích ảnh tham chiếu bằng Vision: {e}")
            return {"prompt_en": "", "description_vi": ""}

    # ── Avatar Generation (GPT Image) ────────────────────────────────

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
        Generate an avatar image using OpenAI's latest image models.

        Strategy (June 2026):
        1. gpt-image-2 — flagship model, best quality & photorealism
        2. gpt-image-1 — fallback if gpt-image-2 unavailable
        3. DiceBear SVG — free fallback (always works)

        Note: DALL-E 2 & DALL-E 3 were retired by OpenAI on May 12, 2026.
        """
        import logging
        import hashlib
        import base64

        # ── 1. Try GPT Image models (gpt-image-2 → gpt-image-1) ──
        for img_model in ["gpt-image-2", "gpt-image-1"]:
            try:
                client = get_openai_client()
                response = await client.images.generate(
                    model=img_model,
                    prompt=prompt[:32000],
                    n=1,
                    size=size,
                )
                image_data = response.data[0]
                revised_prompt = getattr(image_data, 'revised_prompt', prompt)

                # GPT Image models return b64_json
                if getattr(image_data, 'b64_json', None):
                    img_bytes = base64.b64decode(image_data.b64_json)
                    saved = await cls.save_upload(
                        file_data=img_bytes,
                        original_filename=f"avatar_{uuid.uuid4().hex[:8]}.png",
                        subfolder="avatars",
                    )
                    return {
                        "url": saved["url"],
                        "local_path": saved["path"],
                        "revised_prompt": revised_prompt,
                        "source": img_model,
                    }

                # Fallback: if model returns url instead of b64
                image_url = getattr(image_data, 'url', None)
                if image_url:
                    import httpx
                    async with httpx.AsyncClient(timeout=60) as http:
                        img_resp = await http.get(image_url)
                        if img_resp.status_code == 200:
                            saved = await cls.save_upload(
                                file_data=img_resp.content,
                                original_filename=f"avatar_{uuid.uuid4().hex[:8]}.png",
                                subfolder="avatars",
                            )
                            return {
                                "url": saved["url"],
                                "local_path": saved["path"],
                                "revised_prompt": revised_prompt,
                                "source_url": image_url,
                                "source": img_model,
                            }
                    return {"url": image_url, "revised_prompt": revised_prompt, "source": img_model}

                logging.warning(f"{img_model}: response có data nhưng không có b64_json hoặc url")
            except Exception as e:
                err_msg = str(e)[:200]
                logging.warning(f"{img_model} unavailable: {err_msg}")
                if "401" in err_msg or "403" in err_msg:
                    break  # Auth issue — skip all models
                continue

        # ── 2. DiceBear với thông tin cá nhân hóa (Fallback miễn phí) ──
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
        return {"url": avatar_url, "revised_prompt": prompt, "source_url": avatar_url, "source": "dicebear", "note": "Không sinh được ảnh bằng GPT Image (vui lòng kiểm tra số dư tài khoản OpenAI). Sử dụng DiceBear làm ảnh thay thế."}

    @classmethod
    async def generate_avatar_lite(cls, prompt: str) -> dict[str, Any]:
        """Generate avatar using DiceBear (free)."""
        import hashlib
        seed = hashlib.md5(prompt.encode()).hexdigest()
        return {"url": f"https://api.dicebear.com/9.x/avataaars/svg?seed={seed}", "source": "dicebear"}
