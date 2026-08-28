"""
SolicitudPresenter — transforma la entidad Solicitud a esquema HTTP SolicitudOut.
"""
from modules.tramites.domain.models.solicitud import Solicitud
from modules.asignaciones.domain.models import SolicitudAsignacion
from modules.asignaciones.domain.constants import TipoParticipacion
from modules.tramites.presentation.schemas.solicitud_out import SolicitudOut, AsignacionOut
from modules.tramites.presentation.presenters.expediente_presenter import (
    ExpedientePresenter,
)


class SolicitudPresenter:
    """
    Transforma objetos Solicitud del dominio a esquemas de respuesta HTTP.
    Desacopla el formateo de respuesta de los controladores.
    """

    @staticmethod
    def present(solicitud: Solicitud) -> SolicitudOut:
        """
        Transforma una entidad Solicitud a SolicitudOut.

        Incluye expediente con archivos y lista de asignaciones con área y período.

        Args:
            solicitud: Entidad Solicitud del modelo de dominio

        Returns:
            Esquema SolicitudOut listo para respuesta HTTP
        """
        # Load asignaciones with area and periods (eager loading)
        asignaciones_qs = (
            SolicitudAsignacion.objects
            .filter(solicitud=solicitud)
            .select_related("area")
            .prefetch_related("periodos")
        )

        asignaciones_out = [
            SolicitudPresenter._map_asignacion(a)
            for a in asignaciones_qs
        ]

        return SolicitudOut(
            id=solicitud.id,
            expediente=ExpedientePresenter.present(solicitud.expediente),
            estado=solicitud.estado,
            prioridad=solicitud.prioridad,
            fecha_registro=solicitud.fecha_registro,
            fecha_inicio_gestion=solicitud.fecha_inicio_gestion,
            observacion=solicitud.observacion,
            asignaciones=asignaciones_out,
        )

    @staticmethod
    def _map_asignacion(asignacion: SolicitudAsignacion) -> AsignacionOut:
        """
        Transforma una SolicitudAsignacion a AsignacionOut.

        Obtiene el tipo_participacion del período activo (más reciente, ABIERTO).
        """
        # Obtener el período más reciente (abierta o cerrada)
        periodo = (
            asignacion.periodos.all()
            .order_by("-numero_ciclo")
            .first()
        )
        tipo_participacion = periodo.tipo_participacion if periodo else TipoParticipacion.PRINCIPAL

        return AsignacionOut(
            id=asignacion.id,
            area_id=asignacion.area.id,
            area_nombre=asignacion.area.nombre,
            tipo_participacion=tipo_participacion,
            bloquea_cierre=asignacion.bloquea_cierre,
            fecha_incorporacion=asignacion.fecha_incorporacion,
            observacion=asignacion.observacion,
        )
