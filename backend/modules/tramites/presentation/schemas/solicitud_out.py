"""
Esquemas HTTP response para Solicitud — Schema Ninja para API.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from ninja import Field

from core.types import BaseSchema
from modules.tramites.domain.constants import EstadoSolicitud, Prioridad
from modules.tramites.presentation.schemas.expediente_list_out import ExpedienteItemOut


class AsignacionOut(BaseSchema):
    """
    Respuesta HTTP para una asignación de solicitud a área.
    """

    id: UUID = Field(..., description="ID único de la asignación")
    area_id: UUID = Field(..., description="ID del área asignada")
    area_nombre: str = Field(..., description="Nombre del área")
    tipo_participacion: str = Field(..., description="Tipo de participación (PRINCIPAL o ADJUNTA)")
    bloquea_cierre: bool = Field(..., description="¿Bloquea el cierre de la solicitud?")
    fecha_incorporacion: datetime = Field(..., description="Fecha de incorporación del área")
    observacion: Optional[str] = Field(None, description="Observación de la asignación")


class SolicitudOut(BaseSchema):
    """
    Respuesta HTTP para una solicitud creada.

    Incluye expediente anidado completo y lista de asignaciones.
    """

    id: UUID = Field(..., description="ID único de la solicitud")
    expediente: ExpedienteItemOut = Field(..., description="Expediente asociado (anidado)")
    estado: EstadoSolicitud = Field(..., description="Estado actual de la solicitud")
    prioridad: Prioridad = Field(..., description="Prioridad del trámite")
    fecha_registro: datetime = Field(..., description="Fecha de registro")
    fecha_inicio_gestion: Optional[datetime] = Field(
        None,
        description="Fecha en que se empezó a gestionar la solicitud",
    )
    observacion: Optional[str] = Field(None, description="Observación")
    asignaciones: list[AsignacionOut] = Field(default_factory=list, description="Áreas asignadas a la solicitud")
