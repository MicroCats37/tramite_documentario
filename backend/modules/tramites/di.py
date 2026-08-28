"""
Módulo Tramites — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
Se registra en settings vía NINJA_EXTRA["INJECTOR_MODULES"].
"""
from injector import Module, singleton, Binder

from modules.tramites.domain.services.core.expediente_core_service import ExpedienteCoreService
from modules.tramites.domain.services.core.expediente_archivo_core_service import ExpedienteArchivoCoreService
from modules.tramites.domain.services.core.solicitud_core_service import SolicitudCoreService
from modules.tramites.domain.services.flujos.expediente_flujo import ExpedienteCreacionFlujo
from modules.tramites.domain.services.flujos.solicitud_flujo import (
    SolicitudCreacionFlujo,
    SolicitudAreaOperacionesFlujo,
)
from modules.tramites.domain.services.orchestrators.expediente_orchestrator import ExpedienteOrchestrator
from modules.tramites.domain.services.orchestrators.solicitud_orchestrator import SolicitudOrchestrator


class TramitesModule(Module):
    """
    Módulo DI para el paquete tramites.

    Vincula:
    - ExpedienteCoreService (operaciones síncronas de expediente)
    - ExpedienteArchivoCoreService (operaciones síncronas de archivo)
    - SolicitudCoreService (operaciones síncronas de solicitud)
    - ExpedienteCreacionFlujo (flujo de creación de expediente)
    - SolicitudCreacionFlujo (flujo de creación de solicitud)
    - ExpedienteOrchestrator (fachada de expediente)
    - SolicitudOrchestrator (fachada de solicitud)

    Nota: AsignacionCoreService se vincula en AsignacionesModule.
    El injector resuelte automáticamente la dependencia en SolicitudCreacionFlujo.

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        # Core services
        binder.bind(ExpedienteCoreService, to=ExpedienteCoreService, scope=singleton)
        binder.bind(ExpedienteArchivoCoreService, to=ExpedienteArchivoCoreService, scope=singleton)
        binder.bind(SolicitudCoreService, to=SolicitudCoreService, scope=singleton)

        # Flujos
        binder.bind(ExpedienteCreacionFlujo, to=ExpedienteCreacionFlujo, scope=singleton)
        binder.bind(SolicitudCreacionFlujo, to=SolicitudCreacionFlujo, scope=singleton)
        binder.bind(SolicitudAreaOperacionesFlujo, to=SolicitudAreaOperacionesFlujo, scope=singleton)

        # Orchestrators
        binder.bind(ExpedienteOrchestrator, to=ExpedienteOrchestrator, scope=singleton)
        binder.bind(SolicitudOrchestrator, to=SolicitudOrchestrator, scope=singleton)
