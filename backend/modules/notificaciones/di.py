"""Dependency injection wiring for notificaciones module."""

from injector import Module, singleton, Binder

from modules.notificaciones.domain.services.core.notificacion_service import (
    NotificacionService,
)
from modules.notificaciones.domain.services.flujos.notificacion_flujo import (
    NotificacionFlujo,
)
from modules.notificaciones.domain.services.orchestrators.notificacion_orchestrator import (
    NotificacionOrchestrator,
)


class NotificacionesModule(Module):
    """Dependency injection module for notificaciones."""

    def configure(self, binder: Binder) -> None:
        """Configure bindings for notificaciones module."""
        binder.bind(NotificacionService, to=NotificacionService, scope=singleton)
        binder.bind(NotificacionFlujo, to=NotificacionFlujo, scope=singleton)
        binder.bind(
            NotificacionOrchestrator,
            to=NotificacionOrchestrator,
            scope=singleton,
        )
