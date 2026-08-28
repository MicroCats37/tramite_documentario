"""
Esquemas HTTP request para Solicitud — Schema Ninja para API.

Patrón 3: JSON Estricto (sin archivos).
Patrón Dual Payload (FormData + archivos): SolicitudHibridaCreateIn.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from ninja import Field

from core.types import BaseSchema
from modules.tramites.domain.constants import EstadoSolicitud, Prioridad
from modules.asignaciones.domain.constants import TipoParticipacion
from modules.tramites.presentation.schemas.expediente_in import ExpedienteCreateIn


class AreaDistribucionIn(BaseSchema):
    """
    Schema para un área en la distribución de la solicitud.
    """

    area_id: UUID = Field(..., description="ID del área a asignar")
    tipo_participacion: str = Field(
        default=TipoParticipacion.PRINCIPAL,
        description="Tipo de participación: PRINCIPAL o ADJUNTA",
    )
    observacion: Optional[str] = Field(
        None,
        description="Observación opcional al momento de la asignación",
    )


class SolicitudCreateIn(BaseSchema):
    """
    Payload para crear una nueva solicitud.

    Este endpoint NO recibe archivos — solo JSON puro.

    El flujo:
    1. Verifica que el expediente existe y no tiene solicitud asociada.
    2. Crea la Solicitud en estado REGISTRADA.
    3. Crea el historial de estado inicial.
    4. Si hay áreas_distribucion, crea las asignaciones y notificaciones.
    """

    expediente_id: UUID = Field(..., description="ID del expediente asociado")
    prioridad: Prioridad = Field(
        default=Prioridad.MEDIA,
        description="Prioridad del trámite",
    )
    observacion: Optional[str] = Field(
        None,
        description="Observación general de la solicitud",
    )
    areas_distribucion: list[AreaDistribucionIn] = Field(
        default_factory=list,
        description="Lista de áreas a asignar (opcional, puede estar vacía)",
    )


class IncorporarAreaIn(BaseSchema):
    """
    Payload para incorporar un área a una solicitud existente.

    Se usa en POST /solicitudes/{id}/areas.
    Crea una nueva SolicitudAsignacion con su período inicial.
    """

    area_id: UUID = Field(..., description="ID del área a incorporar")
    tipo_participacion: str = Field(
        default=TipoParticipacion.PRINCIPAL,
        description="Tipo de participación: PRINCIPAL o ADJUNTA",
    )
    observacion: Optional[str] = Field(
        None,
        description="Observación opcional al incorporar el área",
    )


class AntecedenteIn(BaseSchema):
    """
    Schema para un antecedente en la creación de solicitud híbrida.
    """

    antecedente_id: UUID = Field(..., description="ID del expediente antecedente")
    categoria: Optional[str] = Field(
        None,
        max_length=100,
        description="Categoría del vínculo (ej: subsanación, recurso)",
    )
    observaciones: Optional[str] = Field(
        None,
        description="Observaciones sobre el antecedente",
    )


class SolicitudHibridaCreateIn(BaseSchema):
    """
    Payload para crear una solicitud con expediente y distribución en una sola operación.

    Combina la creación de Expediente (con archivos adjuntos via dual payload)
    y Solicitud (con distribución de áreas) en un único request HTTP.

    Se recibe via FormData con el patrón dual payload:
        data: JSON string con este schema
        files: lista de UploadedFile con nombres "token___nombre_real.ext"

    El flujo:
    1. Crea el Expediente con sus archivos (transacción atómica).
    2. Crea la Solicitud asociada al expediente en estado REGISTRADA.
    3. Crea el historial de estado inicial.
    4. Si hay áreas_distribucion, establece fecha_inicio_gestion y transiciona a EN_GESTION.
    5. Crea las asignaciones y notificaciones.
    6. Vincula los antecedentes si se proporcionan.
    """

    prioridad: Prioridad = Field(
        default=Prioridad.MEDIA,
        description="Prioridad del trámite",
    )
    observacion: Optional[str] = Field(
        None,
        description="Observación general de la solicitud",
    )
    areas_distribucion: list[AreaDistribucionIn] = Field(
        default_factory=list,
        description="Lista de áreas a asignar (opcional, puede estar vacía)",
    )
    antecedentes: list[AntecedenteIn] = Field(
        default_factory=list,
        description="Lista de expedientes antecedentes (opcional)",
    )
    expediente: ExpedienteCreateIn = Field(
        ...,
        description="Datos del expediente a crear (incluye archivos)",
    )
