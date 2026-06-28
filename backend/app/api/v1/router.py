"""
API v1 Main Router.

Aggregates all v1 route modules. Each phase adds its own router.
Architecture is designed for extensibility — new phases = new routers.
"""

from fastapi import APIRouter

from app.api.v1.persona import router as persona_router
from app.api.v1.story import router as story_router
from app.api.v1.memory import router as memory_router
from app.api.v1.content import router as content_router
from app.api.v1.chat import router as chat_router
from app.api.v1.publishing import router as publishing_router
from app.api.v1.community import router as community_router
from app.api.v1.trend import router as trend_router
from app.api.v1.media import router as media_router
from app.api.v1.automation import router as automation_router
from app.api.v1.monetization import router as monetization_router
from app.api.v1.persona_dna import router as persona_dna_router
from app.api.v1.voice import router as voice_router
from app.api.v1.calendar import router as calendar_router

# ── v1 Main Router ───────────────────────────────────────────────
v1_router = APIRouter(prefix="/api/v1")

# Phase 1: Persona Engine
v1_router.include_router(persona_router, tags=["Persona"])

# Story Engine (the heart)
v1_router.include_router(story_router, tags=["Story"])

# Phase 2: Memory + Life Engine
v1_router.include_router(memory_router, tags=["Memory"])

# Phase 3: Content Engine
v1_router.include_router(content_router, tags=["Content"])

# Phase 4: Publishing Engine
v1_router.include_router(publishing_router, tags=["Publishing"])

# Phase 5: Community Engine
v1_router.include_router(community_router, tags=["Community"])

# Phase 6: Trend Engine
v1_router.include_router(trend_router, tags=["Trend"])

# Chat (cross-phase: uses Persona + Memory)
v1_router.include_router(chat_router, tags=["Chat"])

# Media (image upload & generation)
v1_router.include_router(media_router, tags=["Media"])

# Automation (scheduler + engagement insights)
v1_router.include_router(automation_router, tags=["Automation"])

# Phase 7: Monetization Engine
v1_router.include_router(monetization_router, tags=["Monetization"])

# KOL Studio Phase 1: Persona DNA (Personal Brand Memory Engine)
v1_router.include_router(persona_dna_router, tags=["PersonaDNA"])

# KOL Studio Phase 2: Voice-Match (write in voice + similarity score)
v1_router.include_router(voice_router, tags=["Voice"])

# KOL Studio Phase 3: Content Calendar (30-day funnel plan)
v1_router.include_router(calendar_router, tags=["Calendar"])

# ── Future phases (uncomment as implemented) ────────────────────
# from app.api.v1.monetization import router as monetization_router
# v1_router.include_router(monetization_router, tags=["Monetization"])
#
# from app.api.v1.revenue import router as revenue_router
# v1_router.include_router(revenue_router, tags=["Revenue"])
