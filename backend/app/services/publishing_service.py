"""
Publishing Service — Phase 4: Cross-platform publishing orchestration.

Connects PublishingEngine with:
- SocialAccount management (DB)
- ContentPost management (publishing existing posts)
- Multi-platform simultaneous publishing
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.publishing_engine import (
    Platform,
    PlatformCredentials,
    PublishResult,
    PublishingEngine,
)
from app.models.content import ContentPost
from app.models.social import SocialAccount, SocialPost


class PublishingService:
    """Manages social accounts and cross-platform publishing."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Account Management ───────────────────────────────────────

    async def connect_account(
        self,
        persona_id: str,
        platform: str,
        username: str,
        access_token: str,
        platform_user_id: str | None = None,
    ) -> SocialAccount:
        """Connect a social media account to a persona."""
        # Check if already connected
        existing = await self.db.execute(
            select(SocialAccount).where(
                SocialAccount.persona_id == persona_id,
                SocialAccount.platform == platform,
            )
        )
        account = existing.scalar_one_or_none()

        if account:
            # Update existing
            account.username = username
            account.access_token = access_token
            account.platform_user_id = platform_user_id or account.platform_user_id
            account.is_connected = True
        else:
            # Create new
            account = SocialAccount(
                persona_id=persona_id,
                platform=platform,
                username=username,
                access_token=access_token,
                platform_user_id=platform_user_id,
                is_connected=True,
            )
            self.db.add(account)

        await self.db.flush()
        await self.db.refresh(account)
        return account

    async def get_accounts(
        self,
        persona_id: str,
    ) -> list[SocialAccount]:
        """Get all connected social accounts for a persona."""
        result = await self.db.execute(
            select(SocialAccount).where(
                SocialAccount.persona_id == persona_id,
                SocialAccount.is_connected == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def get_account(self, persona_id: str, platform: str) -> SocialAccount | None:
        """Get a specific connected account."""
        result = await self.db.execute(
            select(SocialAccount).where(
                SocialAccount.persona_id == persona_id,
                SocialAccount.platform == platform,
            )
        )
        return result.scalar_one_or_none()

    async def disconnect_account(self, persona_id: str, platform: str) -> bool:
        """Disconnect a social account."""
        account = await self.get_account(persona_id, platform)
        if not account:
            return False
        account.is_connected = False
        account.access_token = None
        await self.db.flush()
        return True

    # ── Publishing ───────────────────────────────────────────────

    async def publish_post(
        self,
        persona_id: str,
        caption: str,
        platforms: list[str] | None = None,
        media_urls: list[str] | None = None,
        hashtags: list[str] | None = None,
        content_post_id: str | None = None,
        schedule_time: datetime | None = None,
    ) -> list[PublishResult]:
        """
        Publish a post to specified platforms.

        If content_post_id is provided, uses that post's caption/hashtags.
        """
        # If publishing an existing content post
        if content_post_id:
            result = await self.db.execute(
                select(ContentPost).where(ContentPost.id == content_post_id)
            )
            content_post = result.scalar_one_or_none()
            if content_post:
                caption = content_post.caption
                hashtags = content_post.hashtags

        # Get connected accounts
        accounts = await self.get_accounts(persona_id)
        if not accounts:
            return []

        # Filter by requested platforms
        if platforms:
            accounts = [a for a in accounts if a.platform in platforms]

        if not accounts:
            return []

        # Build credentials and publish
        pub_accounts = []
        for account in accounts:
            if not account.access_token:
                continue
            try:
                platform_enum = Platform(account.platform)
                creds = PlatformCredentials(
                    platform=platform_enum,
                    access_token=account.access_token,
                    platform_user_id=account.platform_user_id,
                )
                pub_accounts.append((platform_enum, creds))
            except ValueError:
                continue

        # Publish to all platforms
        results = await PublishingEngine.publish_all(
            accounts=pub_accounts,
            caption=caption,
            media_urls=media_urls,
            hashtags=hashtags,
        )

        # Store successful publishes
        for result in results:
            if result.success:
                # Find matching account
                for account in accounts:
                    if account.platform == result.platform.value:
                        social_post = SocialPost(
                            content_post_id=content_post_id or "",
                            social_account_id=account.id,
                            platform_post_id=result.platform_post_id,
                            platform_post_url=result.platform_post_url,
                            stats=result.stats,
                            published_at=result.published_at or datetime.now(timezone.utc),
                        )
                        self.db.add(social_post)

                        # Update account stats
                        account.posts_count += 1
                        break

        # Update content post status if applicable
        if content_post_id:
            content_post = (
                await self.db.execute(
                    select(ContentPost).where(ContentPost.id == content_post_id)
                )
            ).scalar_one_or_none()
            if content_post:
                all_success = all(r.success for r in results)
                content_post.status = "published" if all_success else "failed"
                content_post.published_at = datetime.now(timezone.utc)

        await self.db.flush()
        return results

    # ── Connection Checks ────────────────────────────────────────

    async def check_connection(
        self,
        platform: str,
        access_token: str,
        platform_user_id: str | None = None,
    ) -> bool:
        """Verify platform credentials are valid."""
        try:
            platform_enum = Platform(platform)
        except ValueError:
            return False

        return await PublishingEngine.check_connection(
            platform=platform_enum,
            credentials=PlatformCredentials(
                platform=platform_enum,
                access_token=access_token,
                platform_user_id=platform_user_id,
            ),
        )

    # ── Stats Fetching ───────────────────────────────────────────

    async def fetch_post_stats(
        self,
        social_post_id: str,
    ) -> dict:
        """Fetch latest engagement stats for a published post."""
        result = await self.db.execute(
            select(SocialPost).where(SocialPost.id == social_post_id)
        )
        post = result.scalar_one_or_none()
        if not post or not post.platform_post_id:
            return {}

        # Get the social account for credentials
        account_result = await self.db.execute(
            select(SocialAccount).where(SocialAccount.id == post.social_account_id)
        )
        account = account_result.scalar_one_or_none()
        if not account or not account.access_token:
            return {}

        try:
            platform_enum = Platform(account.platform)
        except ValueError:
            return {}

        stats = await PublishingEngine.fetch_post_stats(
            platform=platform_enum,
            credentials=PlatformCredentials(
                platform=platform_enum,
                access_token=account.access_token,
            ),
            platform_post_id=post.platform_post_id,
        )

        # Update stored stats
        post.stats = {**post.stats, **stats}
        await self.db.flush()

        return stats
