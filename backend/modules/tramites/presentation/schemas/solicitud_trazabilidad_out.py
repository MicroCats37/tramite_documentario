"""
SolicitudTrazabilidad HTTP schemas — API output for traceability endpoint.

Scope M1.1: Backend traceability output schemas ONLY.
No route, no presenter, no orchestrator, no tests, no migrations.
"""

from datetime import datetime
from uuid import UUID

from ninja import Field

from core.types import BaseSchema


class PeriodoEstadoHistorialOut(BaseSchema):
    """
    State transition record for a periodo (etapa) in the traceability graph.
    """

    estado_anterior: str | None = Field(
        None, description="Previous state before the transition"
    )
    estado_nuevo: str = Field(..., description="New state after the transition")
    fecha_cambio: datetime = Field(..., description="Timestamp of the state change")
    cambiado_por_id: UUID | None = Field(
        None, description="ID of the user who triggered the change"
    )
    cambiado_por_nombres: str = Field(
        ..., description="Full name of the user who triggered the change"
    )
    origen: str | None = Field(
        None, description="Origin of the change (e.g., sistema, usuario)"
    )
    motivo: str | None = Field(
        None, description="Reason or justification for the state change"
    )


class ParticipanteTrazabilidadOut(BaseSchema):
    """
    Participant (usuario) assigned to a periodo in the traceability graph.
    Includes audit fields for assignment and removal.
    """

    usuario_id: UUID = Field(..., description="ID of the participating user")
    usuario_nombres: str = Field(..., description="Full name of the participating user")
    rol: str | None = Field(None, description="Role of the participant in this period")
    fecha_inicio: datetime = Field(
        ..., description="When the participant was added to the period"
    )
    fecha_fin: datetime | None = Field(
        None, description="When the participant was removed (None if still active)"
    )
    activo: bool = Field(
        ..., description="Whether the participant is currently active in this period"
    )
    # Audit fields for assignment
    asignado_por_id: UUID | None = Field(
        None, description="ID of the user who assigned this participant"
    )
    asignado_por_nombres: str | None = Field(
        None, description="Full name of the user who assigned this participant"
    )
    # Audit fields for removal
    retirado_por_id: UUID | None = Field(
        None, description="ID of the user who removed this participant"
    )
    retirado_por_nombres: str | None = Field(
        None, description="Full name of the user who removed this participant"
    )
    motivo_retiro: str | None = Field(
        None, description="Reason why the participant was removed"
    )


class RespuestaTrazabilidadOut(BaseSchema):
    """
    Formal response emitted during a periodo in the traceability graph.
    Metadata-oriented; excludes large formal content unless explicitly needed.
    """

    id: UUID = Field(..., description="Unique ID of the response")
    tipo_respuesta: str = Field(
        ..., description="Type: INFORME, OBSERVACION, CONFORMIDAD, DESCARGO, OTRO"
    )
    contenido: str | None = Field(
        None, description="Text content of the response (may be None for metadata-only)"
    )
    estado: str = Field(
        ..., description="Current state of the response: PENDIENTE, EMITIDO, etc."
    )
    fecha_emision: datetime = Field(
        ..., description="Timestamp when the response was issued"
    )
    emitido_por_id: UUID | None = Field(
        None, description="ID of the user who issued the response"
    )
    emitido_por_nombres: str | None = Field(
        None, description="Full name of the user who issued the response"
    )


class PeriodoTrazabilidadOut(BaseSchema):
    """
    A period (etapa) within an area assignment in the traceability graph.
    Participants and responses are nested per period, not at assignment level.
    """

    id: UUID = Field(..., description="Unique ID of the period")
    numero_ciclo: int = Field(
        ..., description="Cycle number within the parent area assignment"
    )
    tipo_participacion: str = Field(
        ..., description="Participation type: PRINCIPAL or ADJUNTA"
    )
    estado: str = Field(
        ..., description="Current state of the period: ACTIVO, CERRADO, etc."
    )
    fecha_inicio: datetime = Field(
        ..., description="When the period started"
    )
    fecha_fin: datetime | None = Field(
        None, description="When the period ended (None if still open)"
    )
    tipo_cierre: str | None = Field(
        None, description="How the period was closed: NORMAL, ANULADO, etc."
    )
    # Audit fields for period lifecycle
    iniciado_por_id: UUID | None = Field(
        None, description="ID of the user who initiated this period"
    )
    iniciado_por_nombres: str | None = Field(
        None, description="Full name of the user who initiated this period"
    )
    finalizado_por_id: UUID | None = Field(
        None, description="ID of the user who closed this period"
    )
    finalizado_por_nombres: str | None = Field(
        None, description="Full name of the user who closed this period"
    )
    motivo_cierre: str | None = Field(
        None, description="Reason for closing the period"
    )
    # Nested collections per period
    historial_estados: list[PeriodoEstadoHistorialOut] = Field(
        default_factory=list,
        description="State history for this period",
    )
    participantes: list[ParticipanteTrazabilidadOut] = Field(
        default_factory=list,
        description="Participants assigned to this period",
    )
    respuestas: list[RespuestaTrazabilidadOut] = Field(
        default_factory=list,
        description="Formal responses issued during this period",
    )


class AsignacionTrazabilidadOut(BaseSchema):
    """
    Area assignment within a Solicitud in the traceability graph.
    """

    id: UUID = Field(..., description="Unique ID of the assignment")
    area_id: UUID = Field(..., description="ID of the assigned area")
    area_nombre: str = Field(..., description="Name of the assigned area")
    bloquea_cierre: bool = Field(
        ..., description="Whether this area blocks final closure of the solicitud"
    )
    fecha_incorporacion: datetime = Field(
        ..., description="When the area was incorporated into the solicitud"
    )
    incorporado_por_id: UUID | None = Field(
        None, description="ID of the user who incorporated this area"
    )
    incorporado_por_nombres: str | None = Field(
        None, description="Full name of the user who incorporated this area"
    )
    observacion: str | None = Field(
        None, description="Observation or note on the assignment"
    )
    tipo_actual: str | None = Field(
        None, description="Current participation type for this assignment"
    )
    # Nested periods (etapas) within this assignment
    etapas: list[PeriodoTrazabilidadOut] = Field(
        default_factory=list,
        description="Periods (etapas) within this area assignment",
    )


class HistorialEstadoGlobalOut(BaseSchema):
    """
    Global state transition record for the parent Solicitud.
    """

    estado_anterior: str | None = Field(
        None, description="Previous state before the transition"
    )
    estado_nuevo: str = Field(..., description="New state after the transition")
    fecha_cambio: datetime = Field(
        ..., description="Timestamp of the state change"
    )
    cambiado_por_id: UUID = Field(
        ..., description="ID of the user who triggered the change"
    )
    cambiado_por_nombres: str = Field(
        ..., description="Full name of the user who triggered the change"
    )
    origen: str | None = Field(
        None, description="Origin of the change (e.g., sistema, usuario)"
    )
    observacion: str | None = Field(
        None, description="Observation or note on the state change"
    )


class TimelineEventOut(BaseSchema):
    """
    A single event in the chronological timeline projection.
    Typed metadata fields instead of generic dict[str, Any].
    """

    timestamp: datetime = Field(..., description="When the event occurred")
    tipo: str = Field(
        ...,
        description="Event type: ESTADO_SOLICITUD | AREA_INCORPORADA | "
        "PERIODO_INICIADO | PARTICIPANTE_AGREGADO | PARTICIPANTE_RETIRO | "
        "RESPUESTA_EMITIDA | PERIODO_CERRADO",
    )
    descripcion: str = Field(
        ..., description="Human-readable description of the event"
    )
    actor_nombres: str | None = Field(
        None, description="Full name of the user who triggered the event"
    )
    actor_id: UUID | None = Field(
        None, description="ID of the user who triggered the event"
    )
    # Typed nullable event fields instead of dict[str, Any]
    # These capture common event-specific metadata without a generic dict
    event_area_id: UUID | None = Field(
        None, description="Area ID associated with the event (if applicable)"
    )
    event_periodo_id: UUID | None = Field(
        None, description="Period ID associated with the event (if applicable)"
    )
    event_participante_id: UUID | None = Field(
        None, description="Participant ID associated with the event (if applicable)"
    )
    event_respuesta_id: UUID | None = Field(
        None, description="Response ID associated with the event (if applicable)"
    )
    event_estado_anterior: str | None = Field(
        None, description="Previous state (for state-change events)"
    )
    event_estado_nuevo: str | None = Field(
        None, description="New state (for state-change events)"
    )


class SolicitudTrazabilidadOut(BaseSchema):
    """
    Root schema for GET /solicitudes/{id}/trazabilidad.

    Minimal root — only structural identifiers.
    No duplication of SolicitudDetailOut fields (estado, prioridad, expediente, etc.).
    """

    solicitud_id: UUID = Field(
        ..., description="ID of the parent Solicitud"
    )
    historial_estados: list[HistorialEstadoGlobalOut] = Field(
        default_factory=list,
        description="Global state history for the Solicitud",
    )
    areas: list[AsignacionTrazabilidadOut] = Field(
        default_factory=list,
        description="Area assignments in the traceability graph",
    )
    timeline: list[TimelineEventOut] = Field(
        default_factory=list,
        description="Chronological flat projection of all traceability events",
    )
