"""
FastAPI dependency injection.

Provides reusable dependencies for API routes.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db


# Re-export for convenience
get_db_session = get_db
