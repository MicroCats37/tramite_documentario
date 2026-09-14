"""
Event Registry — modular notification event configuration.

NOTIFICACION_REGISTRY is keyed by (ambito, evento) tuples and maps to
EventConfig objects that describe the notification's category, default audience,
wrapper/presentation kind, and navigation target.

Design principles:
- Plain Python dataclass + dict — no Django TextChoices, no ORM.
- No circular imports: registry is a leaf module that other modules can import
  without creating circular dependency chains.
- Business modules that emit notifications do NOT import from the notificaciones
  domain module directly. They receive the registry entry via composition/DI or
  consult it at the config/wiring layer.
- COMENTARIO_CREADO is registered to keep the legacy generic conversation flow
  runnable; it will be removed when normal-comment notifications are dropped
  in a later batch.

Usage:
    from modules.notificaciones.domain.registry import (
        NOTIFICACION_REGISTRY,
        get_event_config,
        is_registered_event,
        AmbitoNotificacion,
        EventoNotificacion,
    )

    config = get_event_config(AmbitoNotificacion.SOLICITUD, EventoNotificacion.ASIGNACION_CREADA)
    if config is not None:
        print(config.categoria)  # INSTITUCIONAL
        print(config.default_audiencia)  # AREA
"""

from dataclasses import dataclass
from typing import ClassVar

from .constants import AmbitoNotificacion, CategoriaNotificacion, EventoNotificacion


# ── AmbitoAudience helper ──────────────────────────────────────────────────────


class AmbitoAudience:
    """
    Audience type constants used by the registry.

    These describe WHO receives the notification, not the delivery channel.
    - AREA: every active user member of the target area receives a NotificacionUsuario
    - USUARIO: only the named user receives a NotificacionUsuario
    """

    AREA = "AREA"
    USUARIO = "USUARIO"


# ── EventConfig dataclass ──────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class EventConfig:
    """
    Configuration for a registered notification event.

    Attributes:
        categoria: Business category — INSTITUCIONAL, MENSAJERIA, or SISTEMA.
            Determines delivery behaviour and UI grouping.
        default_audiencia: Default audience type — AREA or USUARIO.
            Used to determine how the notification is materialized
            (per-user rows vs per-area rows).
        wrapper_type: The wrapper/kind of the notification for UI/presentation.
            Examples: "solicitud", "solicitud_comentario", "sistema".
        navigation_target: The navigation destination when the user clicks
            the notification. Examples: "solicitud", "comentario", "area".
        prioridad_default: Optional default priority for this event.
            If None, the caller must supply one.
    """

    categoria: str
    default_audiencia: str
    wrapper_type: str
    navigation_target: str
    prioridad_default: str | None = None


# ── Registry ─────────────────────────────────────────────────────────────────


class _AmbitoValues:
    """Ad-hoc enum-like values matching AmbitoNotificacion."""

    SOLICITUD: ClassVar[str] = AmbitoNotificacion.SOLICITUD
    SISTEMA: ClassVar[str] = AmbitoNotificacion.SISTEMA


class _EventoValues:
    """Ad-hoc enum-like values matching EventoNotificacion."""

    ASIGNACION_CREADA: ClassVar[str] = EventoNotificacion.ASIGNACION_CREADA
    DEVOLUCION_CREADA: ClassVar[str] = EventoNotificacion.DEVOLUCION_CREADA
    RESPUESTA_CREADA: ClassVar[str] = EventoNotificacion.RESPUESTA_CREADA
    COMENTARIO_MENCION: ClassVar[str] = EventoNotificacion.COMENTARIO_MENCION
    COMENTARIO_CREADO: ClassVar[str] = EventoNotificacion.COMENTARIO_CREADO
    RECORDATORIO: ClassVar[str] = EventoNotificacion.RECORDATORIO
    RESPUESTA_FINAL: ClassVar[str] = EventoNotificacion.RESPUESTA_FINAL


# Aliases so registry entries are readable without full qualification
_S = _AmbitoValues.SOLICITUD
_X = _AmbitoValues.SISTEMA
_A = _EventoValues.ASIGNACION_CREADA
_D = _EventoValues.DEVOLUCION_CREADA
_R = _EventoValues.RESPUESTA_CREADA
_CM = _EventoValues.COMENTARIO_MENCION
_CC = _EventoValues.COMENTARIO_CREADO
_RE = _EventoValues.RECORDATORIO
_RF = _EventoValues.RESPUESTA_FINAL

# Category aliases
_INST = CategoriaNotificacion.INSTITUCIONAL
_MENSA = CategoriaNotificacion.MENSAJERIA
_SIST = CategoriaNotificacion.SISTEMA

# Audience aliases
_AREA = AmbitoAudience.AREA
_USU = AmbitoAudience.USUARIO

# Priority default alias (use the constant reference for clarity)
from .constants import PrioridadNotificacion

NOTIFICACION_REGISTRY: dict[tuple[str, str], EventConfig] = {
    # ── Solicitud events ────────────────────────────────────────────────────────

    # New area assignment created for a solicitud.
    # Audience: AREA (all active members of the area receive notification).
    (_S, _A): EventConfig(
        categoria=_INST,
        default_audiencia=_AREA,
        wrapper_type="solicitud",
        navigation_target="solicitud",
        prioridad_default=PrioridadNotificacion.NORMAL,
    ),

    # Formal devolution created — área must act.
    (_S, _D): EventConfig(
        categoria=_INST,
        default_audiencia=_AREA,
        wrapper_type="solicitud",
        navigation_target="solicitud",
        prioridad_default=PrioridadNotificacion.ALTA,
    ),

    # Formal response created — área must act.
    (_S, _R): EventConfig(
        categoria=_INST,
        default_audiencia=_AREA,
        wrapper_type="solicitud",
        navigation_target="solicitud",
        prioridad_default=PrioridadNotificacion.ALTA,
    ),

    # User mentioned in a comment (via @username).
    # Audience: USUARIO (the mentioned user only).
    (_S, _CM): EventConfig(
        categoria=_MENSA,
        default_audiencia=_USU,
        wrapper_type="solicitud_comentario",
        navigation_target="comentario",
        prioridad_default=PrioridadNotificacion.NORMAL,
    ),

    # Normal comment created (no mention).
    # NOTE: This entry exists to keep the legacy generic conversation flow runnable.
    # Normal-comment notifications will be removed in a later contextual batch.
    # Audience: USUARIO (legacy — was routed to user who created the comment).
    (_S, _CC): EventConfig(
        categoria=_MENSA,
        default_audiencia=_USU,
        wrapper_type="solicitud_comentario",
        navigation_target="comentario",
        prioridad_default=PrioridadNotificacion.NORMAL,
    ),

    # System reminder for a solicitud.
    # Audience: AREA (all active members of the target area).
    (_S, _RE): EventConfig(
        categoria=_SIST,
        default_audiencia=_AREA,
        wrapper_type="solicitud",
        navigation_target="solicitud",
        prioridad_default=PrioridadNotificacion.NORMAL,
    ),

    # Final institutional response that closes a solicitud.
    # Audience: AREA that issued the response + USUARIO (solicitud creator).
    (_S, _RF): EventConfig(
        categoria=_INST,
        default_audiencia=_AREA,
        wrapper_type="solicitud",
        navigation_target="solicitud",
        prioridad_default=PrioridadNotificacion.ALTA,
    ),

    # ── Sistema events ─────────────────────────────────────────────────────────

    # Generic system-level notification.
    # Audience: AREA (system events are routed to a target area).
    (_X, _RE): EventConfig(
        categoria=_SIST,
        default_audiencia=_AREA,
        wrapper_type="sistema",
        navigation_target="sistema",
        prioridad_default=PrioridadNotificacion.NORMAL,
    ),
}


# ── Lookup helpers ─────────────────────────────────────────────────────────────


def get_event_config(ambito: str, evento: str) -> EventConfig | None:
    """
    Look up the EventConfig for a given (ambito, evento) pair.

    Returns None if the pair is not registered.
    """
    return NOTIFICACION_REGISTRY.get((ambito, evento))


def is_registered_event(ambito: str, evento: str) -> bool:
    """Return True if (ambito, evento) is registered."""
    return (ambito, evento) in NOTIFICACION_REGISTRY
