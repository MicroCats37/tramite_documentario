"""Domain models for notificaciones module."""

from .notificacion import (
    Notificacion,
    NotificacionArea,
    NotificacionUsuario,
)
from .notificacion_solicitud import NotificacionSolicitud
from .notificacion_asignacion import NotificacionAsignacion
from .notificacion_periodo import NotificacionPeriodo

__all__ = [
    "Notificacion",
    "NotificacionArea",
    "NotificacionUsuario",
    "NotificacionSolicitud",
    "NotificacionAsignacion",
    "NotificacionPeriodo",
]
