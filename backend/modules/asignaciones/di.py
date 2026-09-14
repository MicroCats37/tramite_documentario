"""
Módulo Asignaciones — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
Se registra en settings vía NINJA_EXTRA["INJECTOR_MODULES"].
"""
from injector import Module, singleton, Binder

from modules.asignaciones.domain.services.core.asignacion_core_service import (
    AsignacionCoreService,
)
from modules.asignaciones.domain.services.core.periodo_estado_historial_service import (
    PeriodoEstadoHistorialCoreService,
)
from modules.asignaciones.domain.services.flujos.periodo_flujo import (
    PeriodoOperacionesFlujo,
)
from modules.conversaciones.domain.services.core.mensajeria_service import (
    MensajeriaCoreService,
)
from modules.asignaciones.domain.services.orchestrators.periodo_orchestrator import (
    PeriodoOrchestrator,
)
from modules.asignaciones.domain.services.flujos.participacion_usuario_flujo import (
    ParticipacionUsuarioFlujo,
)
from modules.asignaciones.domain.services.orchestrators.participacion_usuario_orchestrator import (
    ParticipacionUsuarioOrchestrator,
)


class AsignacionesModule(Module):
    """
    Módulo DI para el paquete asignaciones.

    Vincula:
    - AsignacionCoreService (operaciones síncronas de asignación)
    - PeriodoEstadoHistorialCoreService (operaciones de historial de estado de período)
    - PeriodoOperacionesFlujo (flujo de operaciones de período)
    - PeriodoOrchestrator (fachada de operaciones de período)
    - ParticipacionUsuarioFlujo (flujo de operaciones de participación de usuario)
    - ParticipacionUsuarioOrchestrator (fachada de operaciones de participación de usuario)

    NotificacionFlujo y NotificacionOrchestrator se migraron a módulos.notificaciones.

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        binder.bind(AsignacionCoreService, to=AsignacionCoreService, scope=singleton)
        binder.bind(
            PeriodoEstadoHistorialCoreService,
            to=PeriodoEstadoHistorialCoreService,
            scope=singleton,
        )
        binder.bind(
            MensajeriaCoreService,
            to=MensajeriaCoreService,
            scope=singleton,
        )
        binder.bind(
            PeriodoOperacionesFlujo,
            to=PeriodoOperacionesFlujo,
            scope=singleton,
        )
        binder.bind(
            PeriodoOrchestrator,
            to=PeriodoOrchestrator,
            scope=singleton,
        )
        binder.bind(
            ParticipacionUsuarioFlujo,
            to=ParticipacionUsuarioFlujo,
            scope=singleton,
        )
        binder.bind(
            ParticipacionUsuarioOrchestrator,
            to=ParticipacionUsuarioOrchestrator,
            scope=singleton,
        )
