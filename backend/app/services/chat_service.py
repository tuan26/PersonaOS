"""
Chat Service — orchestrates persona conversations.

Handles the full chat flow:
1. Load persona + context (memories, events)
2. Generate in-character response via ConversationEngine
3. Summarize and store the interaction as a memory
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.conversation_engine import ConversationEngine
from app.services.memory_service import MemoryService
from app.services.persona_service import PersonaService


class ChatService:
    """Orchestrates persona chat interactions."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.persona_service = PersonaService(db)
        self.memory_service = MemoryService(db)

    async def chat(
        self,
        persona_id: str,
        message: str,
        include_memories: bool = True,
        include_life_events: bool = True,
    ) -> dict:
        """
        Full chat interaction with a persona.

        Args:
            persona_id: Target persona
            message: User's message
            include_memories: Include past memories as context
            include_life_events: Include life events as context

        Returns:
            Dict with persona_name, message (response), context_used
        """
        # 1. Load persona
        persona = await self.persona_service.get(persona_id)
        if not persona:
            raise ValueError(f"Persona not found: {persona_id}")

        # 2. Gather context
        memories = []
        life_events = []

        if include_memories:
            memories = await self.memory_service.get_recent_memories(
                persona_id=persona_id,
                limit=15,
                min_importance=0.2,
            )

        if include_life_events:
            life_events = await self.memory_service.get_recent_events(
                persona_id=persona_id,
                limit=5,
            )

        # 3. Generate response
        response = await ConversationEngine.chat(
            persona=persona,
            message=message,
            memories=memories,
            life_events=life_events,
        )

        # 4. Store as memory (async, don't block response)
        try:
            await self.memory_service.summarize_and_store(
                persona_name=persona.name,
                persona_id=persona_id,
                user_message=message,
                persona_response=response,
            )
        except Exception:
            pass  # Don't fail chat if memory storage fails

        return {
            "persona_id": persona_id,
            "persona_name": persona.name,
            "message": response,
            "context_used": {
                "memories_count": len(memories),
                "life_events_count": len(life_events),
            },
        }
