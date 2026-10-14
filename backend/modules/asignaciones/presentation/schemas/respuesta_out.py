"""
Esquemas HTTP response para Respuesta — Schema Ninja para API.
"""
import uuid as uuid_lib
from datetime import datetime
from typing import Optional

from ninja import Field

from core.types import BaseSchema
from modules.asignaciones.domain.constants import EstadoRespuesta, TipoRespuesta


class RespuestaOut(BaseSchema):
    """
    Respuesta formal de un período en estado BORRADOR.

    Se usa en POST /periodos/{id}/respuestas (crear borrador).
    """

    id: uuid_lib.UUID = Field(..., description="ID único de la respuesta")
    periodo_id: uuid_lib.UUID = Field(..., description="ID del período asociado")
    tipo_respuesta: TipoRespuesta = Field(..., description="Tipo de respuesta")
    contenido: Optional[str] = Field(None, description="Contenido o texto de la respuesta")
    archivo: Optional[str] = Field(None, description="Ruta/URL del archivo adjunto")
    estado: EstadoRespuesta = Field(..., description="Estado de la respuesta (siempre BORRADOR al crear)")
    version: int = Field(..., description="Número de versión")
    observacion: Optional[str] = Field(None, description="Observación adicional")
    # Dates — null para borrador (no hay emisión aún)
    fecha_emision: Optional[datetime] = Field(None, description="Fecha de emisión (null en borrador)")
    emitido_por_id: Optional[uuid_lib.UUID] = Field(None, description="ID del usuario que emitió (null en borrador)")
    # Auditable
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")
