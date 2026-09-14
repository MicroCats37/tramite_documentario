"""
Mensaje results — output DTOs for mensaje-related operations.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ArchivoAdjuntoResult(BaseModel):
    """Output representation of a MensajeArchivoAdjunto."""

    id: UUID
    nombre_original: str
    mime_type: str | None
    tamano_bytes: int | None
    descripcion: str | None = None

    model_config = {"arbitrary_types_allowed": True}


class MencionResult(BaseModel):
    """Output representation of a MensajeMencion."""

    id: UUID
    usuario_id: int

    model_config = {"arbitrary_types_allowed": True}


class MensajeConAdjuntosResult(BaseModel):
    """Output representation of a Mensaje with its attachments and mentions."""

    id: UUID
    conversacion_id: UUID
    autor_usuario_id: int
    contenido: str | None
    tipo: str
    fecha_envio: datetime
    mensaje_padre_id: UUID | None
    editado_at: datetime | None
    eliminado_at: datetime | None
    eliminado_por_id: int | None
    archivos_adjuntos: list[ArchivoAdjuntoResult]
    menciones: list[MencionResult]

    model_config = {"arbitrary_types_allowed": True}


class ConversacionConMensajesResult(BaseModel):
    """Output representation of a Conversacion with its messages loaded."""

    id: UUID
    titulo: str | None
    creada_por_id: int
    fecha_inicio: datetime
    fecha_cierre: datetime | None
    cerrado_por_id: int | None
    estado: str
    mensajes: list[MensajeConAdjuntosResult]

    model_config = {"arbitrary_types_allowed": True}
