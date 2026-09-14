"""
Domain schemas — Pydantic DTOs for internal service use.

These are NOT HTTP schemas (those go in presentation/schemas/).
These reflect what the service layer needs, not what the HTTP client sends.
"""

from modules.conversaciones.domain.schemas.conversacion_schemas import (
    ConversacionCreateData,
    ConversacionUpdateData,
)
from modules.conversaciones.domain.schemas.mensaje_schemas import (
    MensajeCreateData,
    MensajeArchivoAdjuntoData,
    MensajeMencionData,
)

__all__ = [
    "ConversacionCreateData",
    "ConversacionUpdateData",
    "MensajeCreateData",
    "MensajeArchivoAdjuntoData",
    "MensajeMencionData",
]
