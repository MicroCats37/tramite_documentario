"""
Módulo Tramites — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
Se registra en settings vía NINJA_EXTRA["INJECTOR_MODULES"].
"""
import os

from django.conf import settings
from injector import Module, singleton, Binder

from modules.tramites.domain.services.core.expediente_core_service import ExpedienteCoreService
from modules.tramites.domain.services.core.expediente_archivo_core_service import ExpedienteArchivoCoreService
from modules.tramites.domain.services.core.solicitud_core_service import SolicitudCoreService
from modules.tramites.domain.services.core.solicitud_respuesta_core_service import (
    SolicitudRespuestaCoreService,
)
from modules.tramites.domain.services.flujos.expediente_flujo import ExpedienteCreacionFlujo
from modules.tramites.domain.services.flujos.solicitud_flujo import (
    SolicitudCreacionFlujo,
    SolicitudAreaOperacionesFlujo,
)
from modules.tramites.domain.services.flujos.solicitud_respuesta_flujo import (
    SolicitudRespuestaFlujo,
)
from modules.tramites.domain.services.orchestrators.expediente_orchestrator import ExpedienteOrchestrator
from modules.tramites.domain.services.orchestrators.solicitud_orchestrator import SolicitudOrchestrator
from modules.tramites.domain.services.orchestrators.solicitud_respuesta_orchestrator import (
    SolicitudRespuestaOrchestrator,
)
from modules.conversaciones.domain.services.flujos.conversacion_flujo import (
    ConversacionFlujo,
)
from modules.tramites.domain.ports.saaa_ports import AbstractSaaaClient
from modules.tramites.infrastructure.saaa_client import FakeSaaaClient, RealSaaaClient
from core_application.storage.services import AbstractStorageService, SaaaStorageService


class TramitesModule(Module):
    """
    Módulo DI para el paquete tramites.

    Vincula:
    - ExpedienteCoreService (operaciones síncronas de expediente)
    - ExpedienteArchivoCoreService (operaciones síncronas de archivo)
    - SolicitudCoreService (operaciones síncronas de solicitud)
    - SolicitudRespuestaCoreService (operaciones síncronas de respuesta)
    - ExpedienteCreacionFlujo (flujo de creación de expediente)
    - SolicitudCreacionFlujo (flujo de creación de solicitud)
    - SolicitudRespuestaFlujo (flujo de respuesta formal a solicitud)
    - ExpedienteOrchestrator (fachada de expediente)
    - SolicitudOrchestrator (fachada de solicitud)
    - SolicitudRespuestaOrchestrator (fachada de respuesta)

    Nota: AsignacionCoreService se vincula en AsignacionesModule.
    El injector resuelte automáticamente la dependencia en SolicitudCreacionFlujo.

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        # Core services
        binder.bind(ExpedienteCoreService, to=ExpedienteCoreService, scope=singleton)
        binder.bind(ExpedienteArchivoCoreService, to=ExpedienteArchivoCoreService, scope=singleton)
        binder.bind(SolicitudCoreService, to=SolicitudCoreService, scope=singleton)
        binder.bind(SolicitudRespuestaCoreService, to=SolicitudRespuestaCoreService, scope=singleton)

        # Flujos
        binder.bind(ExpedienteCreacionFlujo, to=ExpedienteCreacionFlujo, scope=singleton)
        binder.bind(SolicitudCreacionFlujo, to=SolicitudCreacionFlujo, scope=singleton)
        binder.bind(SolicitudAreaOperacionesFlujo, to=SolicitudAreaOperacionesFlujo, scope=singleton)
        binder.bind(SolicitudRespuestaFlujo, to=SolicitudRespuestaFlujo, scope=singleton)

        # Orchestrators
        binder.bind(ExpedienteOrchestrator, to=ExpedienteOrchestrator, scope=singleton)
        binder.bind(SolicitudOrchestrator, to=SolicitudOrchestrator, scope=singleton)
        binder.bind(SolicitudRespuestaOrchestrator, to=SolicitudRespuestaOrchestrator, scope=singleton)

        # SAAA Client — usa FakeSaaaClient en tests/DEBUG, RealSaaaClient en production
        env_fake = os.environ.get("SAAA_USE_FAKE", "").lower()
        use_fake = env_fake not in ("false", "0", "no") and (
            env_fake != "" or getattr(settings, "SAAA_USE_FAKE", settings.DEBUG)
        )
        if use_fake:
            binder.bind(AbstractSaaaClient, to=FakeSaaaClient, scope=singleton)
        else:
            binder.bind(AbstractSaaaClient, to=RealSaaaClient, scope=singleton)

        # Storage service — wraps AbstractSaaaClient and provides a save() interface
        # that returns either a local path or SAAA pointer string for FileField.name
        binder.bind(AbstractStorageService, to=SaaaStorageService, scope=singleton)
