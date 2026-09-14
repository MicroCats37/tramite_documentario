"""
SolicitudRespuesta HTTP schemas — API input/output for finalizar endpoint.
"""

from datetime import datetime
from uuid import UUID

from ninja import Field

from core.types import BaseSchema
from modules.asignaciones.domain.constants import TipoRespuesta
from modules.tramites.domain.constants import EstadoSolicitud


class ArchivoAdjuntoOut(BaseSchema):
    """Archivo adjunto del mensaje de respuesta."""

    id: UUID
    nombre_original: str
    mime_type: str | None = None
    tamano_bytes: int | None = None


class SolicitudRespuestaOut(BaseSchema):
    """Schema de salida para una SolicitudRespuesta."""

    id: UUID
    solicitud_id: UUID
    area_id: UUID
    area_nombre: str
    periodo_id: UUID | None = None
    tipo_respuesta: str
    contenido: str | None = None
    es_final: bool
    fecha_emision: datetime
    emitido_por_id: UUID
    emitido_por_nombre: str
    archivos: list[ArchivoAdjuntoOut] = Field(default_factory=list)
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
