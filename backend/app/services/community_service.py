"""
Community Service — Phase 5: Auto community interaction.

Orchestrates automated comment replies, likes, and inbox responses.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.community_engine import (
    CommentAnalysis,
    CommunityEngine,
    InteractionAction,
    ReplyResult,
)
from app.models.community import AutoReply, Comment, InboxMessage
from app.services.persona_service import PersonaService


class CommunityService:
    """Manages community interactions: comments, replies, inbox."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.persona_service = PersonaService(db)

    # ── Comment Analysis ─────────────────────────────────────────

    async def analyze_comment(
        self,
        persona_id: str,
        comment_content: str,
        commenter_name: str = "Người dùng",
    ) -> CommentAnalysis:
        """Analyze a single comment for sentiment and action."""
        persona = await self.persona_service.get(persona_id)
        analysis = await CommunityEngine.analyze_comment(
            comment_content=comment_content,
            commenter_name=commenter_name,
        )

        # If action is REPLY, generate the reply
        if analysis.action == InteractionAction.REPLY and persona:
            analysis.suggested_reply = await CommunityEngine.generate_reply(
                persona=persona,
                comment_content=comment_content,
                commenter_name=commenter_name,
                sentiment=analysis.sentiment,
            )

        return analysis

    # ── Auto Reply ───────────────────────────────────────────────

    async def auto_reply_comments(
        self,
        persona_id: str,
        comments: list[dict[str, str]],
        max_replies: int = 50,
        current_mood: str = "bình thường",
    ) -> dict[str, Any]:
        """
        Process a batch of comments: analyze, prioritize, reply.

        Args:
            persona_id: Target persona
            comments: List of {"id": "...", "content": "...", "commenter_name": "..."}
            max_replies: Max number of comments to reply to
            current_mood: Persona's current mood
        """
        persona = await self.persona_service.get(persona_id)
        if not persona:
            raise ValueError(f"Persona not found: {persona_id}")

        # 1. Analyze all comments
        analyses: list[tuple[str, CommentAnalysis]] = []
        for c in comments:
            analysis = await CommunityEngine.analyze_comment(
                comment_content=c["content"],
                commenter_name=c.get("commenter_name", ""),
            )
            analyses.append((c["id"], analysis))

        # 2. Prioritize
        to_reply_ids = set(
            CommunityEngine.prioritize_comments(analyses, max_replies)
        )

        # 3. Execute actions
        results: list[ReplyResult] = []
        replied_count = 0
        liked_count = 0
        ignored_count = 0

        for comment_id, analysis in analyses:
            if comment_id in to_reply_ids and analysis.action == InteractionAction.REPLY:
                # Generate reply
                comment_data = next(
                    (c for c in comments if c["id"] == comment_id), {}
                )
                reply_text = await CommunityEngine.generate_reply(
                    persona=persona,
                    comment_content=comment_data.get("content", ""),
                    commenter_name=comment_data.get("commenter_name", ""),
                    sentiment=analysis.sentiment,
                    current_mood=current_mood,
                )

                # Store comment + reply in DB
                await self._store_comment(
                    persona_id=persona_id,
                    platform=comment_data.get("platform", "unknown"),
                    author_name=comment_data.get("commenter_name", ""),
                    content=comment_data.get("content", ""),
                    sentiment=analysis.sentiment.value,
                    sentiment_score=analysis.sentiment_score,
                    reply_content=reply_text,
                )

                results.append(
                    ReplyResult(
                        comment_id=comment_id,
                        action=InteractionAction.REPLY,
                        reply_text=reply_text,
                        success=True,
                    )
                )
                replied_count += 1

            elif analysis.action == InteractionAction.LIKE:
                results.append(
                    ReplyResult(
                        comment_id=comment_id,
                        action=InteractionAction.LIKE,
                        success=True,
                    )
                )
                liked_count += 1

            else:
                results.append(
                    ReplyResult(
                        comment_id=comment_id,
                        action=InteractionAction.IGNORE,
                        success=True,
                    )
                )
                ignored_count += 1

        return {
            "persona_id": persona_id,
            "total_comments": len(comments),
            "replied": replied_count,
            "liked": liked_count,
            "ignored": ignored_count,
            "results": [
                {
                    "comment_id": r.comment_id,
                    "action": r.action.value,
                    "reply_text": r.reply_text,
                    "success": r.success,
                }
                for r in results
            ],
        }

    # ── Inbox ────────────────────────────────────────────────────

    async def reply_inbox(
        self,
        persona_id: str,
        sender_name: str,
        message_content: str,
        platform: str = "instagram",
    ) -> dict[str, Any]:
        """Generate and store an inbox reply."""
        persona = await self.persona_service.get(persona_id)
        if not persona:
            raise ValueError(f"Persona not found: {persona_id}")

        reply = await CommunityEngine.generate_inbox_reply(
            persona=persona,
            message_content=message_content,
            sender_name=sender_name,
        )

        # Store in DB
        msg = InboxMessage(
            persona_id=persona_id,
            platform=platform,
            sender_name=sender_name,
            content=message_content,
            replied=True,
            reply_content=reply,
        )
        self.db.add(msg)
        await self.db.flush()

        return {
            "persona_id": persona_id,
            "persona_name": persona.name,
            "sender_name": sender_name,
            "reply_content": reply,
        }

    # ── Social Inbox (DMs) ───────────────────────────────────────

    @staticmethod
    def _inbox_status(msg: InboxMessage) -> str:
        """Derive lifecycle status from flags: new -> pending -> replied."""
        if msg.replied:
            return "replied"
        if msg.reply_content:
            return "pending"  # AI drafted a reply, not sent yet
        return "new"

    def _inbox_dict(self, msg: InboxMessage) -> dict[str, Any]:
        return {
            "id": msg.id,
            "persona_id": msg.persona_id,
            "platform": msg.platform,
            "sender_name": msg.sender_name,
            "content": msg.content,
            "replied": msg.replied,
            "reply_content": msg.reply_content,
            "status": self._inbox_status(msg),
            "created_at": msg.created_at,
        }

    async def add_inbox_message(
        self,
        persona_id: str,
        sender_name: str,
        content: str,
        platform: str = "instagram",
    ) -> dict[str, Any]:
        """Store an incoming DM (manual intake) with status 'new'."""
        msg = InboxMessage(
            persona_id=persona_id,
            platform=platform,
            sender_name=sender_name,
            content=content,
            replied=False,
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        return self._inbox_dict(msg)

    async def list_inbox(
        self,
        persona_id: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List inbox DMs, optionally filtered by derived status."""
        result = await self.db.execute(
            select(InboxMessage)
            .where(InboxMessage.persona_id == persona_id)
            .order_by(InboxMessage.created_at.desc())
            .limit(limit)
        )
        msgs = list(result.scalars().all())
        out = [self._inbox_dict(m) for m in msgs]
        if status and status != "all":
            out = [m for m in out if m["status"] == status]
        return out

    async def draft_inbox_reply(self, message_id: str) -> dict[str, Any] | None:
        """Generate an in-character reply for a DM (status -> pending)."""
        result = await self.db.execute(
            select(InboxMessage).where(InboxMessage.id == message_id)
        )
        msg = result.scalar_one_or_none()
        if not msg:
            return None

        persona = await self.persona_service.get(msg.persona_id)
        if not persona:
            raise ValueError(f"Persona not found: {msg.persona_id}")

        reply = await CommunityEngine.generate_inbox_reply(
            persona=persona,
            message_content=msg.content,
            sender_name=msg.sender_name,
        )
        msg.reply_content = reply
        msg.replied = False
        await self.db.flush()
        await self.db.refresh(msg)
        return self._inbox_dict(msg)

    async def mark_inbox_replied(self, message_id: str) -> dict[str, Any] | None:
        """Mark a DM as replied (sent)."""
        result = await self.db.execute(
            select(InboxMessage).where(InboxMessage.id == message_id)
        )
        msg = result.scalar_one_or_none()
        if not msg:
            return None
        msg.replied = True
        await self.db.flush()
        await self.db.refresh(msg)
        return self._inbox_dict(msg)

    async def fetch_inbox(
        self,
        persona_id: str,
        platform: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Prep for Phase B: fetch real DMs from the platform.
        Requires a connected account with messaging permissions
        (Instagram/Messenger DM API + app review). Degrades gracefully.
        """
        from app.models.social import SocialAccount

        res = await self.db.execute(
            select(SocialAccount).where(
                SocialAccount.persona_id == persona_id,
                SocialAccount.platform == platform,
                SocialAccount.is_connected == True,  # noqa: E712
            )
        )
        acc = res.scalar_one_or_none()
        if not acc or not acc.access_token:
            return {
                "fetched": 0,
                "messages": [],
                "note": f"Chưa kết nối {platform} (hoặc thiếu token). "
                        f"Vào tab Đăng bài → Kết nối tài khoản trước.",
            }
        return {
            "fetched": 0,
            "messages": [],
            "note": "Kéo DM thật cần quyền nhắn tin (Instagram/Messenger DM API + "
                    "app được duyệt). Tính năng sẵn sàng khi có token đủ quyền.",
        }

    # ── Auto Reply Rules ─────────────────────────────────────────

    async def create_rule(
        self,
        persona_id: str,
        trigger_keywords: list[str],
        reply_template: str,
        trigger_sentiment: str | None = None,
        is_active: bool = True,
        priority: int = 0,
    ) -> AutoReply:
        """Create an auto-reply rule."""
        rule = AutoReply(
            persona_id=persona_id,
            trigger_keywords=trigger_keywords,
            trigger_sentiment=trigger_sentiment,
            reply_template=reply_template,
            is_active=is_active,
            priority=priority,
        )
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def get_rules(self, persona_id: str) -> list[AutoReply]:
        """Get auto-reply rules for a persona."""
        result = await self.db.execute(
            select(AutoReply)
            .where(AutoReply.persona_id == persona_id)
            .order_by(AutoReply.priority.desc())
        )
        return list(result.scalars().all())

    async def fetch_comments(
        self,
        persona_id: str,
        platform: str,
        platform_post_id: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Fetch real comments for a published post from the platform API and store them.
        Requires a connected account (with valid token) for that platform.
        Degrades gracefully (returns a note) when not available.
        """
        from app.engine.publishing_engine import (
            Platform,
            PlatformCredentials,
            PublishingEngine,
        )
        from app.models.social import SocialAccount

        res = await self.db.execute(
            select(SocialAccount).where(
                SocialAccount.persona_id == persona_id,
                SocialAccount.platform == platform,
                SocialAccount.is_connected == True,  # noqa: E712
            )
        )
        acc = res.scalar_one_or_none()
        if not acc or not acc.access_token:
            return {
                "fetched": 0,
                "comments": [],
                "note": f"Chưa kết nối tài khoản {platform} (hoặc thiếu access token). "
                        f"Vào tab Đăng bài → Kết nối tài khoản trước.",
            }

        try:
            plat = Platform(platform)
        except ValueError:
            return {"fetched": 0, "comments": [], "note": f"Nền tảng {platform} không hỗ trợ kéo comment."}

        raw = await PublishingEngine.fetch_comments(
            plat,
            PlatformCredentials(
                platform=plat,
                access_token=acc.access_token,
                platform_user_id=acc.platform_user_id,
            ),
            platform_post_id,
            limit,
        )

        stored: list[Comment] = []
        for c in raw:
            cid = c.get("platform_comment_id")
            if cid:
                dup = await self.db.execute(
                    select(Comment).where(Comment.platform_comment_id == cid)
                )
                if dup.scalar_one_or_none():
                    continue
            comment = Comment(
                persona_id=persona_id,
                platform=platform,
                platform_comment_id=cid,
                post_url=platform_post_id,
                author_name=c.get("author_name", "user"),
                content=c.get("content", ""),
            )
            self.db.add(comment)
            stored.append(comment)
        await self.db.flush()

        note = "" if raw else (
            "API chưa trả về comment. Cần token thật có quyền đọc comment và bài đã đăng thật trên nền tảng."
        )
        return {
            "fetched": len(stored),
            "comments": [
                {"author_name": x.author_name, "content": x.content}
                for x in stored
            ],
            "note": note,
        }

    async def get_comments(
        self,
        persona_id: str,
        limit: int = 50,
    ) -> list[Comment]:
        """Get recent comments for a persona."""
        result = await self.db.execute(
            select(Comment)
            .where(Comment.persona_id == persona_id)
            .order_by(Comment.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ── Helpers ──────────────────────────────────────────────────

    async def _store_comment(
        self,
        persona_id: str,
        platform: str,
        author_name: str,
        content: str,
        sentiment: str,
        sentiment_score: float,
        reply_content: str | None = None,
    ) -> Comment:
        """Store a comment in DB."""
        comment = Comment(
            persona_id=persona_id,
            platform=platform,
            author_name=author_name,
            content=content,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            replied=reply_content is not None,
            reply_content=reply_content,
            replied_at=datetime.now(timezone.utc) if reply_content else None,
        )
        self.db.add(comment)
        await self.db.flush()
        return comment
