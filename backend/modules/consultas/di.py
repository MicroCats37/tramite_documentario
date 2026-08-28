"""
Consultas Module — Cableado de Inyección de Dependencias.

Usa el patrón Module de injector para vincular servicios.
Se registra en settings vía NINJA_EXTRA["INJECTOR_MODULES"].
"""
from django.conf import settings
from injector import Module, singleton, Binder

from modules.consultas.domain.ports import IConsultaClient
from modules.consultas.domain.services.flujos.consulta_externo_flujo import ConsultaExternoFlujo
from modules.consultas.domain.services.orchestrators.consulta_orchestrator import ConsultaOrchestrator
from modules.consultas.infrastructure.services import ConsultaSimulator, RealConsultaClient


class ConsultasModule(Module):
    """
    Módulo DI para el paquete consultas.

    Vincula:
    - IConsultaClient → ConsultaSimulator (DEBUG) o RealConsultaClient (production)
    - ConsultaExternoFlujo
    - ConsultaOrchestrator

    Todos los servicios son de ámbito singleton.
    """

    def configure(self, binder: Binder) -> None:
        # External Clients
        # En DEBUG: usar simulador para desarrollo sin API real
        # En producción: usar cliente real (scraper worker)
        if settings.DEBUG:
            binder.bind(IConsultaClient, to=ConsultaSimulator, scope=singleton)
        else:
            binder.bind(IConsultaClient, to=RealConsultaClient, scope=singleton)

        # Flujos
        binder.bind(ConsultaExternoFlujo, to=ConsultaExternoFlujo, scope=singleton)

        # Orchestrators
        binder.bind(ConsultaOrchestrator, to=ConsultaOrchestrator, scope=singleton)
