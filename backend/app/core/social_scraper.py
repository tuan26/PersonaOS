"""
Social scraper (LOCAL, best-effort) — KOL Studio Phase 1 optional source.

⚠️ Dùng Selenium tự đăng nhập để lấy bài. CHỈ dùng local, cho TÀI KHOẢN CỦA
CHÍNH BẠN, tự chịu rủi ro: việc tự động đăng nhập/đọc vi phạm ToS của hầu hết
nền tảng và có thể bị KHÓA tài khoản. Không dùng cho SaaS bán cho khách.

Thiết kế an toàn nhất có thể:
- Mật khẩu chỉ dùng trong RAM cho phiên đăng nhập, KHÔNG lưu DB/log.
- Dùng user-data-dir riêng để giữ session → đỡ phải đăng nhập lại / 2FA.
- Mặc định non-headless để bạn TỰ giải CAPTCHA/2FA trong cửa sổ trình duyệt.
- Best-effort: selector có thể hỏng khi nền tảng đổi giao diện.
"""

from __future__ import annotations

import time
from typing import Any

from app.config import settings

# Per-platform post selectors (best-effort, will drift over time).
_SELECTORS = {
    "x": ['div[data-testid="tweetText"]'],
    "twitter": ['div[data-testid="tweetText"]'],
    "facebook": ['div[data-ad-comet-preview="message"]', 'div[data-ad-preview="message"]'],
    "tiktok": ['[data-e2e="user-post-item-desc"]', '[data-e2e="browse-video-desc"]'],
    "generic": ["article", "p"],
}

_LOGIN_URL = {
    "x": "https://x.com/login",
    "twitter": "https://x.com/login",
    "facebook": "https://www.facebook.com/login",
    "tiktok": "https://www.tiktok.com/login",
}


def _build_driver(platform: str, headless: bool):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    profile_dir = settings.DATA_DIR / "selenium_profiles" / platform
    profile_dir.mkdir(parents=True, exist_ok=True)

    opts = Options()
    opts.add_argument(f"--user-data-dir={profile_dir}")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1280,2000")
    return webdriver.Chrome(options=opts)


def _try_login(driver, platform: str, username: str, password: str) -> None:
    """Best-effort auto-login. Silently no-ops if the flow doesn't match."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    try:
        driver.get(_LOGIN_URL.get(platform, ""))
        time.sleep(3)
        if platform in ("x", "twitter"):
            box = driver.find_element(By.CSS_SELECTOR, 'input[name="text"]')
            box.send_keys(username, Keys.ENTER)
            time.sleep(2.5)
            pw = driver.find_element(By.CSS_SELECTOR, 'input[name="password"]')
            pw.send_keys(password, Keys.ENTER)
        elif platform == "facebook":
            driver.find_element(By.ID, "email").send_keys(username)
            driver.find_element(By.ID, "pass").send_keys(password, Keys.ENTER)
        time.sleep(4)
    except Exception:
        pass  # fall through to manual login / session reuse


def _logged_in(driver, platform: str) -> bool:
    url = (driver.current_url or "").lower()
    return "login" not in url and "signin" not in url


def _extract(driver, platform: str, max_posts: int) -> list[str]:
    from selenium.webdriver.common.by import By

    selectors = _SELECTORS.get(platform, _SELECTORS["generic"])
    seen: set[str] = set()
    posts: list[str] = []

    scrolls = max(3, max_posts // 4)
    for _ in range(scrolls):
        for sel in selectors:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                t = (el.text or "").strip()
                if len(t) >= 30 and t not in seen:
                    seen.add(t)
                    posts.append(t)
        if len(posts) >= max_posts:
            break
        driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
        time.sleep(2)

    return posts[:max_posts]


def scrape_profile(
    platform: str,
    profile_url: str,
    username: str = "",
    password: str = "",
    max_posts: int = 40,
    headless: bool = False,
    login_wait: int = 90,
) -> dict[str, Any]:
    """
    Open a browser locally, (auto/manual) log in, scrape posts from a profile.
    Returns {posts, note}. Synchronous → call via asyncio.to_thread.
    """
    platform = (platform or "generic").lower()
    driver = None
    try:
        driver = _build_driver(platform, headless)
    except Exception as e:  # noqa: BLE001
        return {"posts": [], "note": f"Không mở được trình duyệt: {str(e)[:160]}. "
                f"Cần Google Chrome cài sẵn."}

    try:
        if username and password:
            _try_login(driver, platform, username, password)

        driver.get(profile_url)
        time.sleep(4)

        # If we hit a login wall and a human can help (non-headless), wait.
        if not _logged_in(driver, platform) and not headless:
            waited = 0
            while waited < login_wait and not _logged_in(driver, platform):
                time.sleep(3)
                waited += 3
            if _logged_in(driver, platform):
                driver.get(profile_url)
                time.sleep(4)

        if not _logged_in(driver, platform):
            return {"posts": [], "note": "Chưa đăng nhập được (có thể dính CAPTCHA/2FA "
                    "hoặc nền tảng chặn). Thử chế độ non-headless để tự đăng nhập."}

        posts = _extract(driver, platform, max_posts)
        if not posts:
            return {"posts": [], "note": "Đăng nhập OK nhưng không trích được bài "
                    "(nền tảng có thể đã đổi giao diện). Thử dán thủ công."}
        return {"posts": posts, "note": f"Đã lấy {len(posts)} bài từ {platform}. "
                "Xem lại & xóa phần không phải bài trước khi phân tích."}
    except Exception as e:  # noqa: BLE001
        return {"posts": [], "note": f"Lỗi scrape: {str(e)[:160]}"}
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
