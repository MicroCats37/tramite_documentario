"""
Dependency injection wiring for conversaciones module.

Registered in INJECTOR_MODULES in settings.
Phase 2: binds MensajeriaCoreService, ConversacionFlujo, ConversacionOrchestrator.
Phase 4: binds SolicitudComentarioFlujo, SolicitudComentarioOrchestrator.
"""

import os

from django.conf import settings
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
from modules.tramites.domain.ports.saaa_ports import AbstractSaaaClient
from modules.tramites.infrastructure.saaa_client import FakeSaaaClient, RealSaaaClient
from core_application.storage.services import AbstractStorageService, SaaaStorageService


class ConversacionesModule(Module):
    """Wires dependencies for the conversaciones module."""

    def configure(self, binder) -> None:
        # SAAA Client — same logic as tramites module
        env_fake = os.environ.get("SAAA_USE_FAKE", "").lower()
        use_fake = env_fake not in ("false", "0", "no") and (
            env_fake != "" or getattr(settings, "SAAA_USE_FAKE", settings.DEBUG)
        )
        if use_fake:
            binder.bind(AbstractSaaaClient, to=FakeSaaaClient, scope=singleton)
        else:
            binder.bind(AbstractSaaaClient, to=RealSaaaClient, scope=singleton)

        # Storage service — used by MensajeriaCoreService for file uploads
        binder.bind(AbstractStorageService, to=SaaaStorageService, scope=singleton)

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
