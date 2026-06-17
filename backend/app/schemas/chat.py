"""
Chat Schemas — for conversing with a persona.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Send a message to a persona."""
    persona_id: str
    message: str = Field(..., min_length=1, max_length=2000)
    # Optional: include recent context
    include_memories: bool = Field(
        default=True,
        description="Include persona's memories in the context"
    )
    include_life_events: bool = Field(
        default=True,
        description="Include recent life events in the context"
    )


class ChatResponse(BaseModel):
    """Persona's response."""
    persona_id: str
    persona_name: str
    message: str
    # Metadata about what influenced the response
    context_used: Optional[dict] = None
