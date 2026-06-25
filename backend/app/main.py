"""
PersonaOS — AI Influencer Operating System
===========================================
FastAPI application entry point.

PersonaOS = Hệ điều hành tạo và vận hành AI Influencer có:
- Danh tính riêng
- Tính cách riêng
- Ký ức riêng
- Cuộc sống riêng
- Nội dung riêng
- Khả năng kiếm tiền riêng
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.v1.router import v1_router
from app.config import settings
from app.core.database import init_db


# ── Application Lifecycle ────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown events."""
    # Startup
    print(f"[START] {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    await init_db()
    print("[OK] Database initialized")
    # Start the in-app scheduler (auto content generation)
    from app.core.scheduler import start_scheduler, shutdown_scheduler
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()
    print("[STOP] Shutting down...")


# ── FastAPI App ──────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## PersonaOS — Hệ điều hành AI Influencer

Tạo ra những "con người số" với danh tính, tính cách, ký ức và cuộc sống riêng.

### 🚀 Các giai đoạn

| Giai đoạn | Engine | Trạng thái |
|-----------|--------|------------|
| 1 | **Persona Engine** — Tạo nhân vật AI | ✅ Hoạt động |
| 2 | **Memory Engine** — Ký ức & Cuộc sống | ✅ Hoạt động |
| 3 | **Content Engine** — Tạo nội dung tự động | ✅ Hoạt động |
| 4 | **Publishing Engine** — Đăng bài đa nền tảng | ✅ Hoạt động |
| 5 | **Community Engine** — Tương tác cộng đồng | ✅ Hoạt động |
| 6 | **Trend Engine** — Phát hiện xu hướng | ✅ Hoạt động |
| 7 | Monetization Engine — Kiếm tiền | 📋 Kế hoạch |
| 8 | Revenue Engine — Tối ưu doanh thu | 📋 Kế hoạch |
| 9 | Multi-Persona Engine — Đa nhân vật | 📋 Kế hoạch |
| 10 | SaaS Platform — Bán hệ thống | 📋 Kế hoạch |

### 🎯 Bắt đầu

1. **Tạo persona**: `POST /api/v1/personas/generate`
2. **Chat với persona**: `POST /api/v1/chat`
3. **Tạo nội dung**: `POST /api/v1/content/generate`
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ───────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────

app.include_router(v1_router)

# ── Static Files (Dashboard UI) ──────────────────────────────────
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/app", StaticFiles(directory=str(static_dir), html=True), name="static")

# ── Media Files (uploads, avatars) ──────────────────────────────
media_dir = settings.MEDIA_DIR
media_dir.mkdir(parents=True, exist_ok=True)
(media_dir / "avatars").mkdir(parents=True, exist_ok=True)
(media_dir / "reference").mkdir(parents=True, exist_ok=True)
from fastapi.staticfiles import StaticFiles
app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")


# ── Root redirect to Dashboard ───────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint — redirect to Dashboard UI."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/app/")


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
    }
