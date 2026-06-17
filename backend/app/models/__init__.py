"""ORM Models: Persona, Memory, Content, Story, Social Inbox, and future-phase models."""

from app.models.persona import Persona
from app.models.memory import Memory, LifeEvent
from app.models.story import Story
from app.models.content import ContentPost, ContentSchedule
from app.models.social import SocialAccount, SocialPost
from app.models.community import Comment, InboxMessage, AutoReply
from app.models.social_inbox import SocialInboxMessage
from app.models.monetization import AffiliateProduct, ClickEvent, ConversionEvent

__all__ = [
    # Phase 1 + Core
    "Persona",
    "Story",
    # Phase 2
    "Memory",
    "LifeEvent",
    # Phase 3
    "ContentPost",
    "ContentSchedule",
    # Phase 4
    "SocialAccount",
    "SocialPost",
    # Phase 5 + Inbox
    "Comment",
    "InboxMessage",
    "AutoReply",
    "SocialInboxMessage",
    # Phase 7-8
    "AffiliateProduct",
    "ClickEvent",
    "ConversionEvent",
]
