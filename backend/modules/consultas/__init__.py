"""
Consultas Module — Consulta de datos externos (DNI/RUC).

Re-exporta el orchestrator para uso удобства.
"""

from .domain.services.orchestrators.consulta_orchestrator import ConsultaOrchestrator

__all__ = ["ConsultaOrchestrator"]
