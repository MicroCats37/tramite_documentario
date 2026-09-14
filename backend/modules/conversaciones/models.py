# Re-export models from domain/models/ — NO logic here.

from .domain.models import (
    Conversacion,
    Mensaje,
    MensajeArchivoAdjunto,
    MensajeMencion,
    SolicitudConversacion,
)

__all__ = [
    "Conversacion",
    "Mensaje",
    "MensajeArchivoAdjunto",
    "MensajeMencion",
    "SolicitudConversacion",
]
