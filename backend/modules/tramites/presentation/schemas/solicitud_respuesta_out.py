"""
SolicitudRespuesta HTTP schemas — API input/output for finalizar endpoint.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional

from ninja import Field

from core.types import BaseSchema
from modules.asignaciones.domain.constants import TipoRespuesta
from modules.tramites.domain.constants import EstadoSolicitud
from modules.tramites.presentation.schemas.archivo_out import ArchivoOut


class SolicitudRespuestaArchivoOut(BaseSchema):
    """
    Archivo adjunto del mensaje de respuesta.

    Wrapper `id` is the contextual row id (MensajeArchivoAdjunto.id).
    Nested `archivo` carries the central Archivo id via `archivo.id`.
    Legacy flat fields (nombre_original, url, mime_type, tamano_bytes)
    preserved for backward compat — consumers should prefer `archivo.*`.
    """

    # Contextual row id — NOT a duplicate of archivo.id
    id: UUID
    # Legacy flat fields
    nombre_original: str
    mime_type: Optional[str] = None
    tamano_bytes: Optional[int] = None
    url: Optional[str] = Field(
        default=None,
        description="URL resolved via resolve_storage_url()",
    )
    # Nested canonical representation — archivo.id is the central Archivo id
    archivo: Optional[ArchivoOut] = Field(
        default=None,
        description="Canonical nested Archivo representation. Use archivo.id as the central Archivo id.",
    )


class SolicitudRespuestaOut(BaseSchema):
    """Schema de salida para una SolicitudRespuesta."""

    id: UUID
    solicitud_id: UUID
    area_id: UUID
    area_nombre: str
    periodo_id: Optional[UUID] = None
    tipo_respuesta: str
    contenido: Optional[str] = None
    es_final: bool
    fecha_emision: datetime
    emitido_por_id: UUID
    emitido_por_nombre: str
    archivos: list[SolicitudRespuestaArchivoOut] = Field(default_factory=list)
    created_at: datetime


class SolicitudRespuestaFinalizarOut(BaseSchema):
    """
    Response wrapper para POST /solicitudes/{id}/finalizar.

    Incluye la respuesta creada, el estado de la solicitud,
    y datos de la conversación y archivos.
    """

    solicitud_respuesta: SolicitudRespuestaOut
    solicitud_estado: EstadoSolicitud
    fecha_cierre: datetime | None = None
    conversacion_id: UUID | None = None
