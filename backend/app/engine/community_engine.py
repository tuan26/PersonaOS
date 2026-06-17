"""
Community Engine — Phase 5: Auto community interaction.

Handles:
- Auto-reply to comments (with persona's voice)
- Auto-like comments
- Auto-reply to inbox messages
- Sentiment analysis for comments
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.core.llm import generate_text
from app.utils.prompt_templates import AUTO_REPLY_SYSTEM


# ── Data Types ───────────────────────────────────────────────────

class CommentSentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class InteractionAction(str, Enum):
    REPLY = "reply"
    LIKE = "like"
    IGNORE = "ignore"
    FLAG = "flag"


@dataclass
class CommentAnalysis:
    """Analysis result for a single comment."""
    sentiment: CommentSentiment
    sentiment_score: float  # 0.0-1.0 confidence
    action: InteractionAction
    suggested_reply: str | None = None
    reason: str = ""


@dataclass
class ReplyResult:
    """Result of an auto-reply action."""
    comment_id: str
    action: InteractionAction
    reply_text: str | None = None
    success: bool = False
    error: str | None = None


# ── Community Engine ─────────────────────────────────────────────

class CommunityEngine:
    """
    Manages automated community interactions.

    Capabilities:
    - Analyze comment sentiment
    - Generate in-character replies
    - Prioritize which comments to reply to
    - Handle inbox messages
    """

    # ── Sentiment Analysis ───────────────────────────────────────

    @staticmethod
    async def analyze_comment(
        comment_content: str,
        commenter_name: str = "",
    ) -> CommentAnalysis:
        """
        Analyze a comment: determine sentiment and best action.

        Uses simple keyword matching + LLM for nuanced cases.
        """
        # Fast path: keyword-based sentiment
        positive_keywords = [
            "dễ thương", "xinh", "đẹp", "tuyệt", "hay", "thích",
            "yêu", "❤", "😍", "🥰", "ngưỡng mộ", "cảm ơn", "hữu ích",
            "giỏi", "pro", "đỉnh", "chất", "ngầu", "cool", "nice",
            "love", "amazing", "great", "awesome", "wow",
            "công nhận", "chuẩn", "đồng ý", "ủng hộ",
        ]
        negative_keywords = [
            "dở", "tệ", "chán", "xấu", "ghét", "dislike",
            "rác", "vô dụng", "lừa đảo", "scam", "fake",
            "😡", "🤬", "troll", "phản cảm", "vô duyên",
            "sai", "không đúng", "bốc phét", "dối trá",
        ]

        lower = comment_content.lower()
        pos_count = sum(1 for kw in positive_keywords if kw in lower)
        neg_count = sum(1 for kw in negative_keywords if kw in lower)

        if pos_count > neg_count:
            sentiment = CommentSentiment.POSITIVE
            score = min(0.95, 0.5 + pos_count * 0.15)
            action = InteractionAction.REPLY
            reason = "Bình luận tích cực"
        elif neg_count > pos_count:
            sentiment = CommentSentiment.NEGATIVE
            score = min(0.95, 0.5 + neg_count * 0.15)
            # Only reply if mildly negative; ignore harsh negativity
            if neg_count > 3:
                action = InteractionAction.IGNORE
                reason = "Bình luận tiêu cực nặng, bỏ qua"
            else:
                action = InteractionAction.REPLY
                reason = "Bình luận tiêu cực nhẹ, có thể phản hồi lịch sự"
        else:
            sentiment = CommentSentiment.NEUTRAL
            score = 0.5
            # Check if it's a question
            if "?" in comment_content or any(
                qw in lower for qw in ["hỏi", "cho hỏi", "có thể", "làm sao", "ở đâu", "bao nhiêu"]
            ):
                action = InteractionAction.REPLY
                reason = "Câu hỏi cần trả lời"
            else:
                action = InteractionAction.LIKE  # Just like it
                reason = "Bình luận trung tính, chỉ thả tim"

        return CommentAnalysis(
            sentiment=sentiment,
            sentiment_score=score,
            action=action,
            reason=reason,
        )

    # ── Reply Generation ─────────────────────────────────────────

    @staticmethod
    async def generate_reply(
        persona: Any,
        comment_content: str,
        commenter_name: str,
        sentiment: CommentSentiment,
        current_mood: str = "bình thường",
    ) -> str:
        """
        Generate an in-character reply to a comment.

        Args:
            persona: Persona ORM object
            comment_content: The user's comment
            commenter_name: Name of the commenter
            sentiment: Detected sentiment
            current_mood: Persona's current mood
        """
        system_prompt = AUTO_REPLY_SYSTEM.format(
            persona_name=persona.name,
            comment_content=comment_content,
            commenter_name=commenter_name,
            current_mood=current_mood,
        )

        # Add persona context to system prompt
        traits = persona.personality.get("traits", [])
        tone = persona.personality.get("tone", "thân thiện")
        speaking_style = persona.personality.get("speaking_style", "tự nhiên")

        full_system = f"""{system_prompt}

Persona context:
- Tính cách: {', '.join(traits) if traits else 'đa dạng'}
- Giọng điệu: {tone}
- Cách nói: {speaking_style}
- Nghề: {persona.occupation}
- Sở thích: {', '.join(persona.interests[:3]) if persona.interests else 'đa dạng'}"""

        reply = await generate_text(
            system_prompt=full_system,
            user_prompt=f"Hãy trả lời comment này: \"{comment_content}\"",
            temperature=0.75,
            use_lite=True,  # GPT-4o-mini cho reply comment
        )

        return reply.strip()

    # ── Comment Prioritization ───────────────────────────────────

    @staticmethod
    def prioritize_comments(
        analyses: list[tuple[str, CommentAnalysis]],
        max_replies: int = 50,
    ) -> list[str]:
        """
        Prioritize which comments to reply to.
        Returns ordered list of comment IDs to reply to.

        Priority:
        1. Questions (high engagement)
        2. Positive comments (build loyalty)
        3. Neutral comments (acknowledge)
        4. Mild negative (handle gracefully)
        """
        # Separate by action
        questions = []
        positives = []
        neutrals = []
        negatives = []

        for comment_id, analysis in analyses:
            if "hỏi" in analysis.reason.lower() or "câu hỏi" in analysis.reason.lower():
                questions.append(comment_id)
            elif analysis.sentiment == CommentSentiment.POSITIVE:
                positives.append(comment_id)
            elif analysis.sentiment == CommentSentiment.NEUTRAL:
                neutrals.append(comment_id)
            elif analysis.action == InteractionAction.REPLY:
                negatives.append(comment_id)

        # Allocate slots
        total = len(questions) + len(positives) + len(neutrals) + len(negatives)
        if total <= max_replies:
            return questions + positives + neutrals + negatives

        # Proportional allocation
        result = []
        # Questions get 40% of slots
        q_slots = min(len(questions), int(max_replies * 0.4))
        result.extend(questions[:q_slots])
        remaining = max_replies - q_slots

        # Positives get 40%
        p_slots = min(len(positives), int(remaining * 0.5))
        result.extend(positives[:p_slots])
        remaining -= p_slots

        # Neutrals get the rest
        n_slots = min(len(neutrals), remaining)
        result.extend(neutrals[:n_slots])
        remaining -= n_slots

        # Any leftover to negatives
        if remaining > 0:
            result.extend(negatives[:remaining])

        return result

    # ── Inbox Handling ───────────────────────────────────────────

    @staticmethod
    async def generate_inbox_reply(
        persona: Any,
        message_content: str,
        sender_name: str,
    ) -> str:
        """
        Generate a reply to a direct/inbox message.
        More personal than comment replies — like texting a friend.
        """
        traits = persona.personality.get("traits", [])
        tone = persona.personality.get("tone", "thân thiện")

        system_prompt = f"""Bạn là {persona.name}, {persona.age}t, {persona.occupation}.
Bạn đang trả lời tin nhắn riêng từ {sender_name}.

Tính cách: {', '.join(traits) if traits else 'thân thiện, tự nhiên'}
Giọng điệu: {tone}

Quy tắc:
1. Trả lời như đang nhắn tin với bạn bè
2. Tự nhiên, gần gũi, có thể dùng emoji
3. Nếu là câu hỏi -> trả lời thật lòng
4. Nếu là khen -> cảm ơn chân thành
5. Nếu là tán tỉnh quá đà -> lịch sự từ chối
6. Giữ bí mật rằng bạn là AI
7. Có thể kể về cuộc sống hàng ngày của bạn"""

        reply = await generate_text(
            system_prompt=system_prompt,
            user_prompt=f"Tin nhắn từ {sender_name}: {message_content}\n\nHãy trả lời:",
            temperature=0.8,
            use_lite=True,  # GPT-4o-mini cho inbox reply
        )

        return reply.strip()
