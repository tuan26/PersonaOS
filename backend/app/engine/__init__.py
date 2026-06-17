"""Engine package — core AI logic for each phase."""

from app.engine.persona_engine import PersonaEngine
from app.engine.conversation_engine import ConversationEngine
from app.engine.memory_engine import MemoryEngine
from app.engine.content_engine import ContentEngine
from app.engine.publishing_engine import PublishingEngine, Platform, PlatformCredentials
from app.engine.community_engine import CommunityEngine, CommentSentiment, InteractionAction
from app.engine.trend_engine import TrendEngine, TrendFetcher, TrendSource, Trend, TrendRecommendation
from app.engine.story_engine import StoryEngine

__all__ = [
    # Phase 1-3
    "PersonaEngine",
    "ConversationEngine",
    "MemoryEngine",
    "ContentEngine",
    # Phase 4
    "PublishingEngine",
    "Platform",
    "PlatformCredentials",
    # Phase 5
    "CommunityEngine",
    "CommentSentiment",
    "InteractionAction",
    # Phase 6
    "TrendEngine",
    "TrendFetcher",
    "TrendSource",
    "Trend",
    "TrendRecommendation",
    # Story Engine
    "StoryEngine",
]
