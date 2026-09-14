"""
SolicitudRespuesta schemas — internal DTOs for the tramites domain.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SolicitudRespuestaCreateData(BaseModel):
    """
    Input data for creating a SolicitudRespuesta.

    Used by the flujo layer. Does not include auto-computed fields
    like area, periodo, emitido_por, conversacion, mensaje, fecha_emision.
    """

    solicitud_id: UUID
    tipo_respuesta: str = Field(..., description="INFORME | OBSERVACION | CONFORMIDAD | DESCARGO | OTRO")
    contenido: str | None = Field(None, description="Contenido textual de la respuesta")
    es_final: bool = Field(False, description="Si True, esta respuesta cierra la solicitud")

    model_config = {"arbitrary_types_allowed": True}
