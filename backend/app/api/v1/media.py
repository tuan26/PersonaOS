"""
Media API — Upload & generate images for personas.
"""

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import settings
from app.services.media_service import MediaService

router = APIRouter(prefix="/media")


@router.post(
    "/upload",
    summary="📤 Upload ảnh tham chiếu",
    description="Upload ảnh người mẫu muốn persona giống. Ảnh sẽ được lưu vào thư mục media/reference/.",
)
async def upload_image(
    file: UploadFile = File(...),
    subfolder: str = Query("reference", description="reference | avatars"),
):
    """Upload ảnh lên server."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Không có file")

    try:
        content = await file.read()
        if len(content) > MediaService.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="File quá lớn (tối đa 10MB)")

        result = await MediaService.save_upload(
            file_data=content,
            original_filename=file.filename,
            subfolder=subfolder,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{subfolder}/{filename}",
    summary="🖼️ Xem ảnh",
)
async def get_image(subfolder: str, filename: str):
    """Lấy ảnh đã upload hoặc sinh ra."""
    file_path = MediaService.get_upload_path(subfolder, filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh")

    # Determine content type
    ext = file_path.suffix.lower()
    content_types = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif",
    }
    return FileResponse(
        file_path,
        media_type=content_types.get(ext, "image/png"),
    )


@router.post(
    "/generate-avatar",
    summary="🤖 Sinh ảnh avatar bằng AI (DALL-E)",
    description="Dùng DALL-E sinh ảnh chân dung nhân vật dựa trên prompt.",
)
async def generate_avatar(
    prompt: str = Query(..., description="Prompt tiếng Anh mô tả avatar"),
    size: str = Query("1024x1024", description="1024x1024 | 512x512 | 256x256"),
    quality: str = Query("standard", description="standard | hd"),
):
    """Sinh ảnh avatar bằng DALL-E."""
    try:
        result = await MediaService.generate_avatar(
            prompt=prompt,
            size=size,
            quality=quality,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi sinh ảnh: {str(e)}")
