"""
Dependency injection wiring for conversaciones module.

Registered in INJECTOR_MODULES in settings.
Phase 2: binds MensajeriaCoreService, ConversacionFlujo, ConversacionOrchestrator.
Phase 4: binds SolicitudComentarioFlujo, SolicitudComentarioOrchestrator.
"""

from injector import Module, singleton

from modules.conversaciones.domain.services.core.mensajeria_service import (
    MensajeriaCoreService,
)
from modules.conversaciones.domain.services.flujos.conversacion_flujo import (
    ConversacionFlujo,
)
from modules.conversaciones.domain.services.flujos.solicitud_comentario_flujo import (
    SolicitudComentarioFlujo,
)
from modules.conversaciones.domain.services.orchestrators.conversacion_orchestrator import (
    ConversacionOrchestrator,
)
from modules.conversaciones.domain.services.orchestrators.solicitud_comentario_orchestrator import (
    SolicitudComentarioOrchestrator,
)


class ConversacionesModule(Module):
    """Wires dependencies for the conversaciones module."""

    def configure(self, binder) -> None:
        binder.bind(MensajeriaCoreService, to=MensajeriaCoreService, scope=singleton)
        binder.bind(ConversacionFlujo, to=ConversacionFlujo, scope=singleton)
        binder.bind(
            ConversacionOrchestrator,
            to=ConversacionOrchestrator,
            scope=singleton,
        )
        binder.bind(
            SolicitudComentarioFlujo,
            to=SolicitudComentarioFlujo,
            scope=singleton,
        )
        binder.bind(
            SolicitudComentarioOrchestrator,
            to=SolicitudComentarioOrchestrator,
            scope=singleton,
        )
