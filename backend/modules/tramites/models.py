# Re-export models from domain/models/ — NO logic here.

from .domain.models import (
    Expediente,
    ExpedienteArchivo,
    ExpedienteAntecedente,
    Solicitud,
    SolicitudEstadoHistorial,
    SolicitudRespuesta,
)

__all__ = [
    "Expediente",
    "ExpedienteArchivo",
    "ExpedienteAntecedente",
    "Solicitud",
    "SolicitudEstadoHistorial",
    "SolicitudRespuesta",
]
