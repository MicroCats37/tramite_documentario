# Core services — operaciones ORM síncronas sin transaction.atomic() propio.

from modules.tramites.domain.services.core.expediente_core_service import ExpedienteCoreService
from modules.tramites.domain.services.core.expediente_archivo_core_service import ExpedienteArchivoCoreService
from modules.tramites.domain.services.core.solicitud_core_service import SolicitudCoreService

__all__ = [
    "ExpedienteCoreService",
    "ExpedienteArchivoCoreService",
    "SolicitudCoreService",
]
