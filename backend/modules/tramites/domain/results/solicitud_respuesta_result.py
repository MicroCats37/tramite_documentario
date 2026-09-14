"""
SolicitudRespuesta result — DTO returned by domain services.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SolicitudRespuestaResult(BaseModel):
    """
    Result object returned by the flujo after creating a SolicitudRespuesta.

    Includes the created response plus context needed by the presenter.
    """

    respuesta_id: UUID
    solicitud_id: UUID
    conversacion_id: UUID
    mensaje_id: UUID
    area_id: UUID
    area_nombre: str
    periodo_id: UUID | None
    tipo_respuesta: str
    contenido: str | None
    es_final: bool
    fecha_emision: datetime
    emitido_por_id: UUID
    emitido_por_nombre: str
    mensaje_archivos: list[dict] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
