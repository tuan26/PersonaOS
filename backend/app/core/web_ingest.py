"""
Web ingest — KOL Studio Phase 1 helper: pull a KOL's public posts from a
profile/page URL so their Persona DNA can be learned without manual paste.

Honest about reality: most social platforms (Instagram, TikTok, Facebook, X)
block server-side scraping (login walls / JS-rendered / anti-bot). This module
does a best-effort fetch and works well for:
- RSS / Atom feeds (Substack, Medium, blogs, YouTube channel RSS)
- Personal websites / blog articles (HTML → text)
and degrades gracefully with a clear note for blocked platforms.

No heavy deps: httpx + stdlib (regex, html, xml.etree).
"""

from __future__ import annotations

import html as htmllib
import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlparse

import httpx

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_BLOCKED = {
    "instagram.com": "Instagram chặn đọc tự động (cần login). Hãy copy vài bài rồi dán vào ô trên.",
    "tiktok.com": "TikTok chặn đọc tự động. Hãy copy caption vài video rồi dán vào ô trên.",
    "facebook.com": "Facebook chặn đọc tự động (cần login). Hãy copy vài bài rồi dán vào ô trên.",
    "x.com": "X (Twitter) chặn đọc tự động. Hãy copy vài tweet rồi dán vào ô trên.",
    "twitter.com": "X (Twitter) chặn đọc tự động. Hãy copy vài tweet rồi dán vào ô trên.",
}

_MAX_POSTS = 60
_MAX_LEN = 1500


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().lstrip("www.")
    except Exception:
        return ""


def _is_private(host: str) -> bool:
    if not host:
        return True
    if host in ("localhost", "0.0.0.0", "::1") or host.endswith(".local"):
        return True
    return bool(
        re.match(r"^(127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.)", host)
    )


def _clean(text: str) -> str:
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = htmllib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:_MAX_LEN]


def _parse_feed(text: str) -> list[str]:
    """Parse RSS/Atom — take title + description/content per item."""
    posts: list[str] = []
    try:
        root = ET.fromstring(text.encode("utf-8", "ignore"))
    except Exception:
        return posts
    for el in root.iter():
        tag = el.tag.split("}")[-1].lower()
        if tag not in ("item", "entry"):
            continue
        title, body = "", ""
        for ch in el:
            t = ch.tag.split("}")[-1].lower()
            if t == "title" and ch.text:
                title = ch.text
            elif t in ("description", "summary", "encoded", "content"):
                body = (ch.text or "") or body
        combined = _clean(f"{title}. {body}" if body else title)
        if len(combined) >= 30:
            posts.append(combined)
        if len(posts) >= _MAX_POSTS:
            break
    return posts


def _parse_html(html: str) -> list[str]:
    """Extract readable text blocks from a webpage."""
    html = re.sub(r"(?is)<(script|style|noscript|head)[^>]*>.*?</\1>", " ", html)
    blocks = re.findall(
        r"(?is)<(?:p|li|h[1-3]|blockquote)[^>]*>(.*?)</(?:p|li|h[1-3]|blockquote)>",
        html,
    )
    seen: set[str] = set()
    posts: list[str] = []
    for b in blocks:
        t = _clean(b)
        if len(t) >= 40 and t not in seen:
            seen.add(t)
            posts.append(t)
        if len(posts) >= _MAX_POSTS:
            break
    return posts


def _youtube_rss(url: str) -> str | None:
    """Map a YouTube channel URL to its RSS feed (only works for /channel/UC...)."""
    m = re.search(r"youtube\.com/channel/(UC[\w-]+)", url)
    if m:
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={m.group(1)}"
    return None


async def fetch_posts_from_url(url: str) -> dict[str, Any]:
    """
    Best-effort fetch of a KOL's public posts from a URL.
    Returns {posts, source_type, note}.
    """
    url = (url or "").strip()
    if not re.match(r"^https?://", url, re.I):
        return {"posts": [], "source_type": "invalid", "note": "Link phải bắt đầu bằng http(s)://"}

    host = _host(url)
    if _is_private(host):
        return {"posts": [], "source_type": "blocked", "note": "Không cho phép link nội bộ/private."}

    # Known blocked platforms → fail fast with guidance
    for dom, msg in _BLOCKED.items():
        if host == dom or host.endswith("." + dom):
            return {"posts": [], "source_type": "blocked_platform", "note": msg}

    fetch_url = _youtube_rss(url) or url

    try:
        async with httpx.AsyncClient(
            timeout=20.0, follow_redirects=True, headers={"User-Agent": _UA}
        ) as client:
            resp = await client.get(fetch_url)
    except Exception as e:  # noqa: BLE001
        return {"posts": [], "source_type": "error", "note": f"Không tải được link: {str(e)[:120]}"}

    if resp.status_code != 200:
        return {
            "posts": [],
            "source_type": "error",
            "note": f"Trang trả về mã {resp.status_code}. Có thể cần đăng nhập — hãy dán bài thủ công.",
        }

    body = resp.text or ""
    ctype = resp.headers.get("content-type", "").lower()
    head = body[:600].lower()

    is_feed = "xml" in ctype or "rss" in head or "<feed" in head or "<rss" in head
    posts = _parse_feed(body) if is_feed else _parse_html(body)
    source_type = "feed" if is_feed else "html"

    if not posts:
        return {
            "posts": [],
            "source_type": source_type,
            "note": "Không trích được nội dung (trang có thể dùng JavaScript hoặc chặn bot). "
                    "Thử link RSS/blog/website, hoặc dán bài thủ công.",
        }

    note = f"Đã lấy {len(posts)} đoạn từ {host} ({'RSS' if is_feed else 'website'}). "
    note += "Hãy xem lại & xóa đoạn không phải bài của KOL trước khi phân tích."
    return {"posts": posts, "source_type": source_type, "note": note}
