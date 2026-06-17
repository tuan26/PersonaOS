"""
Persona Schemas — request/response validation for Persona API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Request Schemas ──────────────────────────────────────────────

class PersonaCreate(BaseModel):
    """Manual creation of a persona (without AI generation)."""
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=16, le=120)
    gender: str = Field(default="nữ")
    occupation: str = Field(..., min_length=1, max_length=200)
    location: str = Field(default="Việt Nam")
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    personality: dict[str, Any] = Field(default_factory=dict)
    interests: list[str] = Field(default_factory=list)
    life_goals: list[dict[str, Any]] = Field(default_factory=list)
    backstory: Optional[str] = None


class PersonaGenerateRequest(BaseModel):
    """Request to AI-generate a persona."""
    concept: str = Field(
        default="",
        description="Mô tả concept tổng thể. Càng chi tiết AI càng tạo nhân vật hay"
    )
    # ── User-specified concrete values (AI MUST respect these) ──
    name: Optional[str] = Field(default=None, description="Tên nhân vật (bắt buộc)")
    nickname: Optional[str] = Field(default=None, description="Biệt danh (bắt buộc)")
    age: Optional[int] = Field(default=None, ge=16, le=60, description="Tuổi cụ thể")
    gender: Optional[str] = Field(default=None, description="Giới tính (nam/nữ/khác)")
    occupation: Optional[str] = Field(default=None, description="Nghề nghiệp cụ thể")
    location: str = Field(default="Việt Nam")
    language: str = Field(default="vi", description="Ngôn ngữ chính của persona")
    # ── Appearance hints ──
    appearance_hint: Optional[str] = Field(default=None, description="Mô tả ngoại hình CHI TIẾT")
    looks_like: Optional[str] = Field(default=None, description="Giống ai. VD: 'Elly Trần'")
    voice_hint: Optional[str] = Field(default=None, description="Giọng nói")
    personality_type: Optional[str] = Field(default=None, description="introvert/extrovert/ambivert")
    fashion_hint: Optional[str] = Field(default=None, description="Phong cách thời trang")
    unique_appeal: Optional[str] = Field(default=None, description="Điểm thu hút đặc biệt")
    interests_hint: Optional[str] = Field(default=None, description="Sở thích, cách nhau dấu phẩy")
    # ── Legacy hints ──
    age_range: Optional[str] = Field(default=None, description="Khoảng tuổi. VD: '20-30'")
    occupation_hint: Optional[str] = Field(default=None, description="Gợi ý nghề nghiệp")
    reference_image_urls: list[str] = Field(
        default_factory=list,
        description="URLs ảnh tham chiếu đã upload"
    )
    creativity: float = Field(default=0.8, ge=0.0, le=1.0)


class PersonaUpdate(BaseModel):
    """Partial update of a persona."""
    name: Optional[str] = None
    nickname: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=16, le=120)
    gender: Optional[str] = None
    occupation: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_gen_prompt: Optional[str] = None
    concept_description: Optional[str] = None
    appearance: Optional[dict[str, Any]] = None
    fashion_style: Optional[str] = None
    unique_appeal: Optional[str] = None
    voice_style: Optional[str] = None
    personality_type: Optional[str] = None
    personality: Optional[dict[str, Any]] = None
    interests: Optional[list[str]] = None
    life_goals: Optional[list[dict[str, Any]]] = None
    relationships: Optional[list[dict[str, Any]]] = None
    backstory: Optional[str] = None
    is_active: Optional[bool] = None


class RegenerateFieldRequest(BaseModel):
    """Request to regenerate a single field using AI."""
    field: str = Field(..., description="Tên field cần regenerate: name|nickname|age|occupation|fashion_style|unique_appeal|appearance|voice_style|personality_type|interests|life_goals|relationships")
    context: Optional[dict[str, Any]] = Field(default=None, description="Context hiện tại của persona để AI giữ consistency")


# ── Response Schemas ─────────────────────────────────────────────

class PersonaResponse(BaseModel):
    """Full persona response."""
    id: str
    name: str
    nickname: Optional[str] = None
    age: int
    gender: str
    occupation: str
    location: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_gen_prompt: Optional[str] = None
    concept_description: Optional[str] = None
    appearance: dict[str, Any]
    fashion_style: Optional[str] = None
    unique_appeal: Optional[str] = None
    voice_style: str
    personality_type: str
    personality: dict[str, Any]
    interests: list[str]
    life_goals: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    backstory: Optional[str] = None
    is_active: bool
    follower_count: int
    total_earnings: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PersonaSummary(BaseModel):
    """Brief persona summary for list views."""
    id: str
    name: str
    nickname: Optional[str] = None
    age: int
    gender: str
    occupation: str
    location: str
    avatar_url: Optional[str] = None
    concept_description: Optional[str] = None
    appearance: Optional[dict[str, Any]] = None
    fashion_style: Optional[str] = None
    unique_appeal: Optional[str] = None
    voice_style: str
    personality_type: str
    personality: Optional[dict[str, Any]] = None
    interests: list[str]
    life_goals: Optional[list[dict[str, Any]]] = None
    relationships: Optional[list[dict[str, Any]]] = None
    backstory: Optional[str] = None
    is_active: bool
    follower_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
