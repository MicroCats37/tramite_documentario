"""
Conversacion schemas — DTOs for conversacion-related operations.
"""

from datetime import datetime, timezone as dt_timezone
from uuid import UUID

from pydantic import BaseModel, Field


def _now():
    return datetime.now(dt_timezone.utc)


class ConversacionCreateData(BaseModel):
    """Input data for creating a Conversacion."""

    titulo: str | None = Field(default=None, max_length=255)
    creada_por_id: UUID = Field(description="UUID of the user creating the conversation")
    fecha_inicio: datetime = Field(default_factory=_now)

    model_config = {"arbitrary_types_allowed": True}


class ConversacionUpdateData(BaseModel):
    """Input data for updating a Conversacion."""

    titulo: str | None = Field(default=None, max_length=255)
    fecha_cierre: datetime | None = None
    cerrado_por_id: UUID | None = None

    model_config = {"arbitrary_types_allowed": True}


class ConversacionCloseData(BaseModel):
    """Input data for closing a Conversacion."""

    cerrado_por_id: UUID = Field(description="UUID of the user closing the conversation")

    model_config = {"arbitrary_types_allowed": True}
