"""
Publishing Engine — Phase 4: Auto-publish content to social platforms.

Supports:
- TikTok, Instagram, Facebook, Threads, X (Twitter)

Architecture: Platform Adapter pattern — each platform has its own adapter
implementing a common interface. Adding a new platform = adding a new adapter.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx

from app.config import settings


# ── Data Types ───────────────────────────────────────────────────

class Platform(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    THREADS = "threads"
    X = "x"


class PostStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass
class PublishResult:
    """Result of a publish attempt."""
    success: bool
    platform: Platform
    platform_post_id: str | None = None
    platform_post_url: str | None = None
    error_message: str | None = None
    published_at: datetime | None = None
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlatformCredentials:
    """Credentials for a social platform."""
    platform: Platform
    access_token: str
    platform_user_id: str | None = None
    refresh_token: str | None = None
    expires_at: datetime | None = None


# ── Base Adapter ─────────────────────────────────────────────────

class BasePlatformAdapter(ABC):
    """
    Abstract base for all platform adapters.
    Each platform (TikTok, Instagram, etc.) implements this interface.
    """

    platform: Platform

    def __init__(self, credentials: PlatformCredentials):
        self.credentials = credentials
        self.client = httpx.AsyncClient(timeout=30.0)

    @abstractmethod
    async def publish_post(
        self,
        caption: str,
        media_urls: list[str] | None = None,
        hashtags: list[str] | None = None,
        schedule_time: datetime | None = None,
    ) -> PublishResult:
        """Publish a post to the platform."""
        ...

    @abstractmethod
    async def get_post_stats(self, platform_post_id: str) -> dict[str, Any]:
        """Get engagement stats for a post."""
        ...

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Check if credentials are valid."""
        ...

    async def close(self):
        await self.client.aclose()

    def _build_hashtag_string(self, hashtags: list[str] | None) -> str:
        """Build hashtag string from list."""
        if not hashtags:
            return ""
        return " ".join(
            f"#{tag.strip().replace(' ', '')}" for tag in hashtags
        )

    def _full_caption(self, caption: str, hashtags: list[str] | None = None) -> str:
        """Combine caption and hashtags."""
        parts = [caption]
        if hashtags:
            parts.append("\n.\n.\n.\n" + self._build_hashtag_string(hashtags))
        return "\n\n".join(parts)


# ── Platform Adapters ────────────────────────────────────────────

class TikTokAdapter(BasePlatformAdapter):
    """TikTok publishing via TikTok API."""

    platform = Platform.TIKTOK
    BASE_URL = "https://open-api.tiktok.com/v2"

    async def publish_post(
        self,
        caption: str,
        media_urls: list[str] | None = None,
        hashtags: list[str] | None = None,
        schedule_time: datetime | None = None,
    ) -> PublishResult:
        """Post to TikTok."""
        try:
            full_caption = self._full_caption(caption, hashtags)

            # TikTok API: POST /video/publish/ or /video/upload/
            payload = {
                "access_token": self.credentials.access_token,
                "open_id": self.credentials.platform_user_id,
                "text": full_caption[:2200],  # TikTok caption limit
            }

            if media_urls:
                payload["video_url"] = media_urls[0]

            response = await self.client.post(
                f"{self.BASE_URL}/video/publish/",
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()
                return PublishResult(
                    success=True,
                    platform=self.platform,
                    platform_post_id=data.get("data", {}).get("video_id"),
                    published_at=datetime.now(timezone.utc),
                )
            else:
                return PublishResult(
                    success=False,
                    platform=self.platform,
                    error_message=f"TikTok API error: {response.text}",
                )

        except Exception as e:
            return PublishResult(
                success=False,
                platform=self.platform,
                error_message=str(e),
            )

    async def get_post_stats(self, platform_post_id: str) -> dict[str, Any]:
        """Get TikTok video stats."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/video/query/",
                params={
                    "access_token": self.credentials.access_token,
                    "open_id": self.credentials.platform_user_id,
                    "video_id": platform_post_id,
                },
            )
            if response.status_code == 200:
                data = response.json().get("data", {})
                return {
                    "views": data.get("view_count", 0),
                    "likes": data.get("like_count", 0),
                    "comments": data.get("comment_count", 0),
                    "shares": data.get("share_count", 0),
                }
        except Exception:
            pass
        return {}

    async def validate_credentials(self) -> bool:
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/user/info/",
                params={
                    "access_token": self.credentials.access_token,
                    "open_id": self.credentials.platform_user_id,
                },
            )
            return response.status_code == 200
        except Exception:
            return False


class InstagramAdapter(BasePlatformAdapter):
    """Instagram publishing via Instagram Graph API."""

    platform = Platform.INSTAGRAM
    BASE_URL = "https://graph.instagram.com/v21.0"

    async def publish_post(
        self,
        caption: str,
        media_urls: list[str] | None = None,
        hashtags: list[str] | None = None,
        schedule_time: datetime | None = None,
    ) -> PublishResult:
        try:
            full_caption = self._full_caption(caption, hashtags)

            ig_user_id = self.credentials.platform_user_id

            if media_urls:
                # Step 1: Create media container
                container_payload = {
                    "caption": full_caption[:2200],
                    "access_token": self.credentials.access_token,
                }

                if len(media_urls) > 1:
                    # Carousel
                    container_payload["media_type"] = "CAROUSEL"
                    # First create individual containers, then carousel...
                    # Simplified for now: single image/video
                    container_payload["image_url"] = media_urls[0]
                else:
                    container_payload["image_url"] = media_urls[0]

                container_resp = await self.client.post(
                    f"{self.BASE_URL}/{ig_user_id}/media",
                    json=container_payload,
                )
                container_data = container_resp.json()

                if "id" not in container_data:
                    return PublishResult(
                        success=False,
                        platform=self.platform,
                        error_message=f"Container creation failed: {container_data}",
                    )

                creation_id = container_data["id"]

                # Step 2: Publish container
                publish_resp = await self.client.post(
                    f"{self.BASE_URL}/{ig_user_id}/media_publish",
                    json={
                        "creation_id": creation_id,
                        "access_token": self.credentials.access_token,
                    },
                )
                publish_data = publish_resp.json()

                return PublishResult(
                    success="id" in publish_data,
                    platform=self.platform,
                    platform_post_id=publish_data.get("id"),
                    platform_post_url=f"https://instagram.com/p/{publish_data.get('id')}",
                    published_at=datetime.now(timezone.utc),
                )
            else:
                return PublishResult(
                    success=False,
                    platform=self.platform,
                    error_message="Instagram requires at least one media URL",
                )

        except Exception as e:
            return PublishResult(success=False, platform=self.platform, error_message=str(e))

    async def get_post_stats(self, platform_post_id: str) -> dict[str, Any]:
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/{platform_post_id}/insights",
                params={
                    "access_token": self.credentials.access_token,
                    "metric": "engagement,impressions,reach",
                },
            )
            if response.status_code == 200:
                data = response.json().get("data", [])
                stats = {}
                for item in data:
                    stats[item["name"]] = item.get("values", [{}])[0].get("value", 0)
                return stats
        except Exception:
            pass
        return {}

    async def validate_credentials(self) -> bool:
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/me",
                params={"access_token": self.credentials.access_token},
            )
            return response.status_code == 200
        except Exception:
            return False


class FacebookAdapter(BasePlatformAdapter):
    """Facebook publishing via Graph API."""

    platform = Platform.FACEBOOK
    BASE_URL = "https://graph.facebook.com/v21.0"

    async def publish_post(
        self,
        caption: str,
        media_urls: list[str] | None = None,
        hashtags: list[str] | None = None,
        schedule_time: datetime | None = None,
    ) -> PublishResult:
        try:
            full_caption = self._full_caption(caption, hashtags)
            page_id = self.credentials.platform_user_id

            payload: dict[str, Any] = {
                "message": full_caption[:63206],
                "access_token": self.credentials.access_token,
            }

            if media_urls:
                if len(media_urls) > 1:
                    # Multiple photos
                    for i, url in enumerate(media_urls):
                        payload[f"attached_media[{i}]"] = json.dumps({"media_fbid": url})
                else:
                    payload["link"] = media_urls[0]

            if schedule_time:
                payload["scheduled_publish_time"] = int(schedule_time.timestamp())
                payload["published"] = "false"

            response = await self.client.post(
                f"{self.BASE_URL}/{page_id}/feed",
                json=payload,
            )
            data = response.json()

            if "id" in data:
                return PublishResult(
                    success=True,
                    platform=self.platform,
                    platform_post_id=data["id"],
                    platform_post_url=f"https://facebook.com/{data['id']}",
                    published_at=datetime.now(timezone.utc),
                )
            else:
                return PublishResult(
                    success=False,
                    platform=self.platform,
                    error_message=data.get("error", {}).get("message", str(data)),
                )

        except Exception as e:
            return PublishResult(success=False, platform=self.platform, error_message=str(e))

    async def get_post_stats(self, platform_post_id: str) -> dict[str, Any]:
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/{platform_post_id}",
                params={
                    "access_token": self.credentials.access_token,
                    "fields": "likes.summary(true),comments.summary(true),shares",
                },
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "likes": data.get("likes", {}).get("summary", {}).get("total_count", 0),
                    "comments": data.get("comments", {}).get("summary", {}).get("total_count", 0),
                    "shares": data.get("shares", {}).get("count", 0),
                }
        except Exception:
            pass
        return {}

    async def validate_credentials(self) -> bool:
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/me",
                params={"access_token": self.credentials.access_token},
            )
            return response.status_code == 200
        except Exception:
            return False


class ThreadsAdapter(BasePlatformAdapter):
    """Threads publishing via Threads API (Meta)."""

    platform = Platform.THREADS
    BASE_URL = "https://graph.threads.net/v1.0"

    async def publish_post(
        self,
        caption: str,
        media_urls: list[str] | None = None,
        hashtags: list[str] | None = None,
        schedule_time: datetime | None = None,
    ) -> PublishResult:
        try:
            full_caption = self._full_caption(caption, hashtags)
            threads_user_id = self.credentials.platform_user_id

            if media_urls:
                # Step 1: Create media container
                container_resp = await self.client.post(
                    f"{self.BASE_URL}/{threads_user_id}/threads",
                    json={
                        "media_type": "IMAGE",
                        "image_url": media_urls[0],
                        "text": full_caption[:500],
                        "access_token": self.credentials.access_token,
                    },
                )
                container_data = container_resp.json()

                if "id" not in container_data:
                    return PublishResult(
                        success=False,
                        platform=self.platform,
                        error_message=f"Container failed: {container_data}",
                    )

                # Step 2: Publish
                publish_resp = await self.client.post(
                    f"{self.BASE_URL}/{threads_user_id}/threads_publish",
                    json={
                        "creation_id": container_data["id"],
                        "access_token": self.credentials.access_token,
                    },
                )
                publish_data = publish_resp.json()

                return PublishResult(
                    success="id" in publish_data,
                    platform=self.platform,
                    platform_post_id=publish_data.get("id"),
                    published_at=datetime.now(timezone.utc),
                )
            else:
                # Text-only post
                response = await self.client.post(
                    f"{self.BASE_URL}/{threads_user_id}/threads",
                    json={
                        "media_type": "TEXT",
                        "text": full_caption[:500],
                        "access_token": self.credentials.access_token,
                    },
                )
                data = response.json()

                if "id" in data:
                    # Publish immediately
                    pub_resp = await self.client.post(
                        f"{self.BASE_URL}/{threads_user_id}/threads_publish",
                        json={
                            "creation_id": data["id"],
                            "access_token": self.credentials.access_token,
                        },
                    )
                    pub_data = pub_resp.json()
                    return PublishResult(
                        success="id" in pub_data,
                        platform=self.platform,
                        platform_post_id=pub_data.get("id"),
                        published_at=datetime.now(timezone.utc),
                    )

                return PublishResult(
                    success=False,
                    platform=self.platform,
                    error_message=str(data),
                )

        except Exception as e:
            return PublishResult(success=False, platform=self.platform, error_message=str(e))

    async def get_post_stats(self, platform_post_id: str) -> dict[str, Any]:
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/{platform_post_id}/insights",
                params={
                    "access_token": self.credentials.access_token,
                    "metric": "views,likes,replies,reposts,quotes",
                },
            )
            if response.status_code == 200:
                data = response.json().get("data", [])
                stats = {}
                for item in data:
                    stats[item["name"]] = item.get("values", [{}])[0].get("value", 0)
                return stats
        except Exception:
            pass
        return {}

    async def validate_credentials(self) -> bool:
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/me",
                params={"access_token": self.credentials.access_token},
            )
            return response.status_code == 200
        except Exception:
            return False


class XAdapter(BasePlatformAdapter):
    """X (Twitter) publishing via X API v2."""

    platform = Platform.X
    BASE_URL = "https://api.x.com/2"

    async def publish_post(
        self,
        caption: str,
        media_urls: list[str] | None = None,
        hashtags: list[str] | None = None,
        schedule_time: datetime | None = None,
    ) -> PublishResult:
        try:
            full_text = caption[:280]  # X's character limit
            if hashtags:
                hashtag_str = " " + self._build_hashtag_string(hashtags[:3])
                full_text = caption[: (280 - len(hashtag_str))] + hashtag_str

            payload: dict[str, Any] = {"text": full_text}

            if media_urls:
                # Upload media first via v1.1 API, then attach to tweet
                media_ids = []
                for url in media_urls[:4]:  # X max 4 images
                    try:
                        media_id = await self._upload_media(url)
                        if media_id:
                            media_ids.append(media_id)
                    except Exception:
                        pass
                if media_ids:
                    payload["media"] = {"media_ids": media_ids}

            response = await self.client.post(
                f"{self.BASE_URL}/tweets",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.credentials.access_token}",
                    "Content-Type": "application/json",
                },
            )
            data = response.json()

            if "data" in data:
                tweet_id = data["data"]["id"]
                return PublishResult(
                    success=True,
                    platform=self.platform,
                    platform_post_id=tweet_id,
                    platform_post_url=f"https://x.com/i/status/{tweet_id}",
                    published_at=datetime.now(timezone.utc),
                )
            else:
                return PublishResult(
                    success=False,
                    platform=self.platform,
                    error_message=data.get("detail", str(data)),
                )

        except Exception as e:
            return PublishResult(success=False, platform=self.platform, error_message=str(e))

    async def _upload_media(self, media_url: str) -> str | None:
        """Upload media to X and return media_id."""
        try:
            # Download media
            dl_resp = await self.client.get(media_url)
            if dl_resp.status_code != 200:
                return None

            # Upload to X v1.1
            upload_resp = await self.client.post(
                "https://upload.x.com/1.1/media/upload.json",
                files={"media": dl_resp.content},
                headers={"Authorization": f"Bearer {self.credentials.access_token}"},
            )
            data = upload_resp.json()
            return data.get("media_id_string")
        except Exception:
            return None

    async def get_post_stats(self, platform_post_id: str) -> dict[str, Any]:
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/tweets/{platform_post_id}",
                params={
                    "tweet.fields": "public_metrics",
                },
                headers={"Authorization": f"Bearer {self.credentials.access_token}"},
            )
            if response.status_code == 200:
                metrics = response.json().get("data", {}).get("public_metrics", {})
                return {
                    "views": metrics.get("impression_count", 0),
                    "likes": metrics.get("like_count", 0),
                    "replies": metrics.get("reply_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "quotes": metrics.get("quote_count", 0),
                }
        except Exception:
            pass
        return {}

    async def validate_credentials(self) -> bool:
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/users/me",
                headers={"Authorization": f"Bearer {self.credentials.access_token}"},
            )
            return response.status_code == 200
        except Exception:
            return False


# ── Adapter Factory ──────────────────────────────────────────────

ADAPTER_MAP: dict[Platform, type[BasePlatformAdapter]] = {
    Platform.TIKTOK: TikTokAdapter,
    Platform.INSTAGRAM: InstagramAdapter,
    Platform.FACEBOOK: FacebookAdapter,
    Platform.THREADS: ThreadsAdapter,
    Platform.X: XAdapter,
}


def create_adapter(platform: Platform, credentials: PlatformCredentials) -> BasePlatformAdapter:
    """Factory: create the right adapter for a platform."""
    adapter_class = ADAPTER_MAP.get(platform)
    if not adapter_class:
        raise ValueError(f"Unsupported platform: {platform}")
    return adapter_class(credentials)


# ── Publishing Engine ────────────────────────────────────────────

class PublishingEngine:
    """
    Orchestrates cross-platform publishing.

    Usage:
        engine = PublishingEngine()
        result = await engine.publish_to_platform(
            platform=Platform.INSTAGRAM,
            credentials=creds,
            caption="Hôm nay mèo nhà mình...",
            media_urls=["https://..."],
            hashtags=["meo", "pet", "daily"],
        )
        results = await engine.publish_all(
            accounts=[...],
            caption="...",
            media_urls=[...],
        )
    """

    @staticmethod
    async def publish_to_platform(
        platform: Platform,
        credentials: PlatformCredentials,
        caption: str,
        media_urls: list[str] | None = None,
        hashtags: list[str] | None = None,
        schedule_time: datetime | None = None,
    ) -> PublishResult:
        """Publish content to a single platform."""
        adapter = create_adapter(platform, credentials)
        try:
            result = await adapter.publish_post(
                caption=caption,
                media_urls=media_urls,
                hashtags=hashtags,
                schedule_time=schedule_time,
            )
            return result
        finally:
            await adapter.close()

    @staticmethod
    async def publish_all(
        accounts: list[tuple[Platform, PlatformCredentials]],
        caption: str,
        media_urls: list[str] | None = None,
        hashtags: list[str] | None = None,
    ) -> list[PublishResult]:
        """Publish to all connected platforms simultaneously."""
        import asyncio

        tasks = []
        for platform, credentials in accounts:
            tasks.append(
                PublishingEngine.publish_to_platform(
                    platform=platform,
                    credentials=credentials,
                    caption=caption,
                    media_urls=media_urls,
                    hashtags=hashtags,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        final_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                final_results.append(
                    PublishResult(
                        success=False,
                        platform=accounts[i][0],
                        error_message=str(r),
                    )
                )
            else:
                final_results.append(r)

        return final_results

    @staticmethod
    async def check_connection(
        platform: Platform,
        credentials: PlatformCredentials,
    ) -> bool:
        """Verify platform credentials are valid."""
        adapter = create_adapter(platform, credentials)
        try:
            return await adapter.validate_credentials()
        finally:
            await adapter.close()

    @staticmethod
    async def fetch_post_stats(
        platform: Platform,
        credentials: PlatformCredentials,
        platform_post_id: str,
    ) -> dict[str, Any]:
        """Fetch engagement stats for a published post."""
        adapter = create_adapter(platform, credentials)
        try:
            return await adapter.get_post_stats(platform_post_id)
        finally:
            await adapter.close()
