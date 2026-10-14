# Re-export models from domain/models/ — NO logic here.

from .domain.models import (
    Archivo,
    Expediente,
    ExpedienteArchivo,
    ExpedienteAntecedente,
    Solicitud,
    SolicitudEstadoHistorial,
    SolicitudRespuesta,
)

__all__ = [
    "Archivo",
    "Expediente",
    "ExpedienteArchivo",
    "ExpedienteAntecedente",
    "Solicitud",
    "SolicitudEstadoHistorial",
    "SolicitudRespuesta",
]
