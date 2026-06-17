"""Pydantic schemas for request/response validation."""

from app.schemas.persona import (
    PersonaCreate,
    PersonaGenerateRequest,
    PersonaResponse,
    PersonaSummary,
    PersonaUpdate,
)
from app.schemas.memory import (
    LifeEventCreate,
    LifeEventResponse,
    MemoryCreate,
    MemoryResponse,
)
from app.schemas.content import (
    ContentGenerateRequest,
    ContentPostResponse,
    ContentScheduleCreate,
    ContentScheduleResponse,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.publishing import (
    PublishRequest,
    PublishAllResponse,
    SocialAccountCreate,
    SocialAccountResponse,
)
from app.schemas.community import (
    AutoReplyRequest,
    AutoReplyResponse,
    CommentAnalyzeRequest,
    CommentAnalyzeResponse,
    InboxReplyRequest,
    InboxReplyResponse,
)
from app.schemas.trend import (
    TrendFetchRequest,
    TrendRecommendRequest,
    TrendRecommendListResponse,
    TrendRecommendationResponse,
    TrendResponse,
)

__all__ = [
    # Persona
    "PersonaCreate",
    "PersonaUpdate",
    "PersonaResponse",
    "PersonaSummary",
    "PersonaGenerateRequest",
    # Memory
    "MemoryCreate",
    "MemoryResponse",
    "LifeEventCreate",
    "LifeEventResponse",
    # Content
    "ContentPostResponse",
    "ContentGenerateRequest",
    "ContentScheduleCreate",
    "ContentScheduleResponse",
    # Chat
    "ChatRequest",
    "ChatResponse",
    # Publishing
    "PublishRequest",
    "PublishAllResponse",
    "SocialAccountCreate",
    "SocialAccountResponse",
    # Community
    "AutoReplyRequest",
    "AutoReplyResponse",
    "CommentAnalyzeRequest",
    "CommentAnalyzeResponse",
    "InboxReplyRequest",
    "InboxReplyResponse",
    # Trend
    "TrendFetchRequest",
    "TrendRecommendRequest",
    "TrendRecommendListResponse",
    "TrendRecommendationResponse",
    "TrendResponse",
]
