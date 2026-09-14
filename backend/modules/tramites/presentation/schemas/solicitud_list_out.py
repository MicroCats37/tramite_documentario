"""
Esquemas HTTP response extendidos para Solicitud — Schema Ninja para API.

Incluye:
- SolicitudItemOut: item resumido para listado paginado
- SolicitudDetailOut: detalle integral consolidado
- AreaActivaOut: área activa en item de listado
- EstadoOperativoOut: resumen calculado del estado operativo
"""
import uuid
from datetime import datetime
from typing import Optional

from ninja import Field

from core.types import BaseSchema
from modules.tramites.domain.constants import EstadoSolicitud, Prioridad
from modules.asignaciones.domain.constants import TipoParticipacion, EstadoPeriodo
from modules.tramites.presentation.schemas.expediente_list_out import ExpedienteItemOut, ExpedienteDetailOut


class ConversacionSummaryOut(BaseSchema):
    """Resumen de conversación vinculada a una solicitud (para detalle)."""

    id: uuid.UUID = Field(..., description="ID de la conversación")
    titulo: Optional[str] = Field(None, description="Título de la conversación")
    estado: str = Field(..., description="Estado de la conversación (ABIERTA o CERRADA)")
    fecha_inicio: datetime = Field(..., description="Fecha de inicio")


class AreaActivaOut(BaseSchema):
    """Área activa en item de listado de solicitudes."""

    area_id: uuid.UUID = Field(..., description="ID del área")
    area_nombre: str = Field(..., description="Nombre del área")
    tipo_participacion: str = Field(..., description="Tipo de participación (PRINCIPAL o ADJUNTA)")
    estado_periodo: str = Field(..., description="Estado del período activo (PENDIENTE o EN_GESTION)")


class SolicitudItemOut(BaseSchema):
    """
    Item resumido de solicitud para listado paginado y respuesta de creación.

    Incluye expediente anidado para reutilización del schema de expediente.
    Todos los datos del expediente están disponibles en el objeto expediente anidado.
    """

    id: uuid.UUID = Field(..., description="ID único de la solicitud")
    expediente: ExpedienteItemOut = Field(..., description="Expediente asociado (anidado)")
    estado: EstadoSolicitud = Field(..., description="Estado actual de la solicitud")
    prioridad: Prioridad = Field(..., description="Prioridad del trámite")
    fecha_registro: datetime = Field(..., description="Fecha de registro")
    fecha_inicio_gestion: Optional[datetime] = Field(None, description="Fecha de inicio de gestión")
    fecha_limite: Optional[datetime] = Field(None, description="Fecha límite")
    areas_activas: list[AreaActivaOut] = Field(default_factory=list, description="Áreas activas con estado de período")
    conteo_pendiente: int = Field(0, description="Cantidad de períodos en estado PENDIENTE")
    conteo_en_gestion: int = Field(0, description="Cantidad de períodos en estado EN_GESTION")


class PeriodoDetalleOut(BaseSchema):
    """Período de asignación con su historial de estados."""

    id: uuid.UUID = Field(..., description="ID del período")
    numero_ciclo: int = Field(..., description="Número de ciclo")
    tipo_participacion: str = Field(..., description="Tipo de participación")
    estado: str = Field(..., description="Estado del período")
    fecha_inicio: datetime = Field(..., description="Fecha de inicio")
    fecha_fin: Optional[datetime] = Field(None, description="Fecha de fin")
    tipo_cierre: Optional[str] = Field(None, description="Tipo de cierre")
    iniciado_por_nombres: Optional[str] = Field(None, description="Quién inició")
    historial_estados: list[dict] = Field(default_factory=list, description="Historial de cambios de estado")


class ParticipanteDetalleOut(BaseSchema):
    """Participante activo o histórico de un período."""

    usuario_id: uuid.UUID = Field(..., description="ID del usuario")
    usuario_nombres: str = Field(..., description="Nombres del usuario")
    rol: Optional[str] = Field(None, description="Rol en el período")
    fecha_inicio: datetime = Field(..., description="Fecha de inicio")
    fecha_fin: Optional[datetime] = Field(None, description="Fecha de fin (null si activo)")
    activo: bool = Field(..., description="¿Está activo?")


class RespuestaDetalleOut(BaseSchema):
    """Respuesta de una asignación Período."""

    id: uuid.UUID = Field(..., description="ID de la respuesta")
    tipo_respuesta: str = Field(..., description="Tipo de respuesta")
    contenido: Optional[str] = Field(None, description="Contenido de la respuesta")
    estado: str = Field(..., description="Estado de la respuesta")
    fecha_emision: Optional[datetime] = Field(None, description="Fecha de emisión")
    emitido_por_nombres: Optional[str] = Field(None, description="Quién emitió")


class AsignacionDetalleOut(BaseSchema):
    """Asignación completa con períodos, participantes y respuestas."""

    id: uuid.UUID = Field(..., description="ID de la asignación")
    area_id: uuid.UUID = Field(..., description="ID del área")
    area_nombre: str = Field(..., description="Nombre del área")
    bloquea_cierre: bool = Field(..., description="¿Bloquea el cierre?")
    fecha_incorporacion: datetime = Field(..., description="Fecha de incorporación")
    observacion: Optional[str] = Field(None, description="Observación")
    periodos: list[PeriodoDetalleOut] = Field(default_factory=list, description="Períodos ordenados por ciclo")
    participantes: list[ParticipanteDetalleOut] = Field(default_factory=list, description="Participantes del último período")
    respuestas: list[RespuestaDetalleOut] = Field(default_factory=list, description="Respuestas del último período")


class HistorialEstadoGlobalOut(BaseSchema):
    """Entrada del historial global de cambios de estado de la solicitud."""

    estado_anterior: Optional[str] = Field(None, description="Estado anterior")
    estado_nuevo: str = Field(..., description="Estado nuevo")
    fecha_cambio: datetime = Field(..., description="Fecha del cambio")
    cambiado_por_nombres: str = Field(..., description="Quién realizó el cambio")
    origen: Optional[str] = Field(None, description="Origen del cambio")
    observacion: Optional[str] = Field(None, description="Observación")


class SolicitudDetailOut(BaseSchema):
    """
    Detalle integral de solicitud para GET /solicitudes/{id}.

    Consolida:
    - Solicitud (con expediente y asignaciones)
    - Historial global de estados
    - Expediente completo con archivos y antecedentes
    - Por cada asignación: períodos ordenados, participantes, respuestas
    """

    # Solicitud fields
    id: uuid.UUID = Field(..., description="ID único de la solicitud")
    estado: EstadoSolicitud = Field(..., description="Estado actual")
    prioridad: Prioridad = Field(..., description="Prioridad")
    fecha_registro: datetime = Field(..., description="Fecha de registro")
    fecha_inicio_gestion: Optional[datetime] = Field(None, description="Fecha de inicio de gestión")
    fecha_limite: Optional[datetime] = Field(None, description="Fecha límite")
    fecha_cierre: Optional[datetime] = Field(None, description="Fecha de cierre")
    observacion: Optional[str] = Field(None, description="Observación")

    # Expediente anidado
    expediente: ExpedienteDetailOut = Field(..., description="Expediente completo con archivos y antecedentes")

    # Historial global de estados
    historial_global: list[HistorialEstadoGlobalOut] = Field(default_factory=list, description="Historial de cambios de estado")

    # Asignaciones con detalle
    asignaciones: list[AsignacionDetalleOut] = Field(default_factory=list, description="Asignaciones con períodos, participantes y respuestas")

    # Conversación vinculada (puede ser None para solicitudes creadas antes de esta característica)
    conversacion: Optional[ConversacionSummaryOut] = Field(None, description="Conversación vinculada a la solicitud")


class EstadoOperativoOut(BaseSchema):
    """
    Resumen calculado del estado operativo de una solicitud.

    No persiste nuevos estados — solo computa métricas.
    """

    total_areas: int = Field(..., description="Total de áreas asignadas")
    areas_pendientes: int = Field(..., description="Áreas con todos sus períodos en PENDIENTE")
    areas_en_gestion: int = Field(..., description="Áreas con al menos un período en EN_GESTION")
    areas_cerradas: int = Field(..., description="Áreas con todos sus períodos en CERRADO")
    con_respuesta: int = Field(..., description="Áreas que tienen al menos una respuesta emitida")
    sin_participantes: int = Field(..., description="Áreas sin participantes activos")
    vencida: bool = Field(..., description="¿Está vencida (fecha_limite < ahora y estado != FINALIZADA)?")
