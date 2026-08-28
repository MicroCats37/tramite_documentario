"""Modelos del módulo asignaciones."""

from .asignacion import SolicitudAsignacion
from .derivacion import SolicitudDerivacion
from .notificacion import Notificacion, NotificacionUsuario
from .periodo import (
    SolicitudAsignacionPeriodo,
    SolicitudAsignacionUsuario,
)
from .periodo_estado_historial import SolicitudAsignacionPeriodoEstadoHistorial
from .respuesta import SolicitudAsignacionRespuesta

__all__ = [
    # Asignación
    "SolicitudAsignacion",
    # Períodos
    "SolicitudAsignacionPeriodo",
    "SolicitudAsignacionUsuario",
    # Historial de estado del período
    "SolicitudAsignacionPeriodoEstadoHistorial",
    # Derivación
    "SolicitudDerivacion",
    # Respuesta
    "SolicitudAsignacionRespuesta",
    # Notificación
    "Notificacion",
    "NotificacionUsuario",
]
