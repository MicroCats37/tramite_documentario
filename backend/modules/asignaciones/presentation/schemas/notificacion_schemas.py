"""
Esquemas HTTP response para Notificacion — Schema Ninja para API.
"""
import uuid
from datetime import datetime
from typing import Optional

from ninja import Field

from core.types import BaseSchema
from modules.asignaciones.domain.constants import TipoNotificacion, EstadoNotificacion


class NotificacionItemOut(BaseSchema):
    """
    Item de notificación para bandeja paginada.
    """

    id: uuid.UUID = Field(..., description="ID único de la notificación")
    tipo: TipoNotificacion = Field(..., description="Tipo de notificación")
    titulo: str = Field(..., description="Título")
    mensaje: Optional[str] = Field(None, description="Mensaje")
    fecha_evento: Optional[datetime] = Field(None, description="Fecha del evento")
    solicitud_id: Optional[uuid.UUID] = Field(None, description="ID de la solicitud asociada")
    expediente_id_publico: Optional[str] = Field(None, description="ID público del expediente")
    area_nombre: str = Field(..., description="Nombre del área")
    periodo_id: Optional[uuid.UUID] = Field(None, description="ID del período asociado")
    interactuada: bool = Field(..., description="¿El usuario ha interactuado con esta notificación?")
    vista: bool = Field(False, description="¿Fue vista?")
    abierta: bool = Field(False, description="¿Fue abierta?")
    descartada: bool = Field(False, description="¿Fue descartada?")


class InteraccionOut(BaseSchema):
    """Interacción de un usuario con una notificación."""

    usuario_id: uuid.UUID = Field(..., description="ID del usuario")
    vista_at: Optional[datetime] = Field(None, description="Cuándo fue vista")
    abierta_at: Optional[datetime] = Field(None, description="Cuándo fue abierta")
    descartada_at: Optional[datetime] = Field(None, description="Cuándo fue descartada")


class NotificacionDetailOut(BaseSchema):
    """
    Detalle completo de una notificación.
    """

    id: uuid.UUID = Field(..., description="ID único de la notificación")
    tipo: TipoNotificacion = Field(..., description="Tipo de notificación")
    titulo: str = Field(..., description="Título")
    mensaje: Optional[str] = Field(None, description="Mensaje")
    estado: EstadoNotificacion = Field(..., description="Estado de la notificación")
    fecha_evento: Optional[datetime] = Field(None, description="Fecha del evento")
    generada_por_nombres: Optional[str] = Field(None, description="Quién generó la notificación")

    # Contexto
    area_id: Optional[uuid.UUID] = Field(None, description="ID del área")
    area_nombre: Optional[str] = Field(None, description="Nombre del área")
    solicitud_id: Optional[uuid.UUID] = Field(None, description="ID de la solicitud")
    expediente_id_publico: Optional[str] = Field(None, description="ID público del expediente")
    expediente_asunto: Optional[str] = Field(None, description="Asunto del expediente")
    periodo_id: Optional[uuid.UUID] = Field(None, description="ID del período")

    # Interacciones del actor actual
    interacciones: list[InteraccionOut] = Field(default_factory=list, description="Interacciones del usuario")
