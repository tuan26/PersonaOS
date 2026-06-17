"""
Persona Model — Phase 1: Persona Engine

Represents an AI Influencer's identity, personality, and core attributes.
This is the central entity; all other engines reference a Persona.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Persona(Base):
    """An AI Influencer persona — a 'digital human' with its own identity."""

    __tablename__ = "personas"

    # ── Identity ─────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False, default="nữ")

    # ── Profile ──────────────────────────────────────────────────
    occupation: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(200), default="Việt Nam")
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Prompt để sinh ảnh avatar bằng DALL-E/Midjourney
    avatar_gen_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Concept (NEW) ────────────────────────────────────────────
    concept_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Mô tả concept tổng thể dài, chi tiết về nhân vật

    # ── Appearance ───────────────────────────────────────────────
    # Structure: {
    #   "description": "Tóc ngắn ngang vai, da trắng, mắt to...",
    #   "style": "năng động, đơn giản",
    #   "reference_images": ["url1", "url2"],
    #   "looks_like": "Giống IU nhưng tóc ngắn",
    #   "height": "1m62",
    #   "body_type": "mảnh mai"
    # }
    appearance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # ── Fashion Style (NEW) ──────────────────────────────────────
    fashion_style: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Mô tả phong cách thời trang: "Thanh lịch, nữ tính, thường mặc váy midi..."

    # ── Unique Appeal (NEW) ──────────────────────────────────────
    unique_appeal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Điểm thu hút đặc biệt: "Nụ cười tỏa nắng, giọng nói truyền cảm..."

    # ── Voice Style (NEW) ────────────────────────────────────────
    # "dịu dàng" | "năng động" | "hài hước" | "trầm tính" | "lầy lội"
    voice_style: Mapped[str] = mapped_column(String(50), default="tự nhiên")

    # ── Personality Type (NEW) ───────────────────────────────────
    # "introvert" | "extrovert" | "ambivert"
    personality_type: Mapped[str] = mapped_column(String(30), default="ambivert")

    # ── Personality Details ──────────────────────────────────────
    # Structure: {
    #   "traits": ["hài hước", "nhiệt tình", "hơi hậu đậu"],
    #   "tone": "thân thiện, gần gũi",
    #   "speaking_style": "hay dùng emoji, nói tắt",
    #   "values": ["gia đình", "tự do", "sáng tạo"],
    #   "quirks": ["hay quên đồ", "thích chụp ảnh mèo"],
    #   "fears": ["sợ độ cao", "sợ cô đơn"],
    #   "pet_phrases": ["Trời ơi", "Đúng bài"]
    # }
    personality: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # ── Interests & Lifestyle ────────────────────────────────────
    interests: Mapped[list[str]] = mapped_column(JSON, default=list)

    # ── Life Goals (NEW: structured) ─────────────────────────────
    # Structure: [
    #   {"goal": "Tiết kiệm 50tr đi Tokyo", "deadline": "2025-12", "progress": 30,
    #    "category": "travel", "status": "in_progress"},
    #   {"goal": "Giảm 5kg", "deadline": "2025-08", "progress": 60,
    #    "category": "health", "status": "in_progress"}
    # ]
    life_goals: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # ── Relationships (NEW) ──────────────────────────────────────
    # Structure: [
    #   {"name": "Miu", "type": "pet", "species": "mèo Anh lông ngắn", "since": "2025-01"},
    #   {"name": "Linh", "type": "best_friend", "occupation": "Designer", "since": "2018"},
    #   {"name": "Anh Khôi", "type": "crush", "occupation": "Photographer", "status": "chưa dám tỏ tình"}
    # ]
    relationships: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # ── Backstory ────────────────────────────────────────────────
    backstory: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Status ───────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(default=True)
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    total_earnings: Mapped[float] = mapped_column(default=0.0)

    # ── AI Generation Meta ───────────────────────────────────────
    generation_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Template used to generate this persona (for reproducibility)

    # ── Timestamps ───────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    memories: Mapped[list["Memory"]] = relationship(  # noqa: F821
        "Memory", back_populates="persona", cascade="all, delete-orphan"
    )
    life_events: Mapped[list["LifeEvent"]] = relationship(  # noqa: F821
        "LifeEvent", back_populates="persona", cascade="all, delete-orphan"
    )
    content_posts: Mapped[list["ContentPost"]] = relationship(  # noqa: F821
        "ContentPost", back_populates="persona", cascade="all, delete-orphan"
    )
    social_accounts: Mapped[list["SocialAccount"]] = relationship(  # noqa: F821
        "SocialAccount", back_populates="persona", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Persona(id={self.id}, name={self.name})>"

    @property
    def summary(self) -> str:
        """One-line summary of this persona."""
        return f"{self.name}, {self.age}t, {self.occupation} - {', '.join(self.interests[:3])}"
