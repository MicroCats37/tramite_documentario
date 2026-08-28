"""
SolicitudCoreService — operaciones ORM síncronas para Solicitud.

NO usa transaction.atomic() internamente — el flujo (flujo) provee la
transacción atómica cuando necesita crear la solicitud junto con asignaciones.
"""
from datetime import datetime

from injector import inject

from modules.tramites.domain.models import Solicitud, SolicitudEstadoHistorial, Expediente
from modules.tramites.domain.constants import EstadoSolicitud


class SolicitudCoreService:
    """
    Operaciones síncronas para Solicitud.

    Toda operación es sync y no abre transaction.atomic() internamente.
    El flujo que la调用 provee la atomicidad si es necesaria.
    """

    def _obtener_expediente_para_solicitud(self, expediente_id) -> Expediente | None:
        """
        Obtiene un expediente por su ID verificando que tenga solicitud null.

        Sync — para uso dentro de transaction.atomic.
        """
        try:
            # Usamos select_related para cargar la relación solicitud si existe
            return Expediente.objects.select_related("solicitud").get(id=expediente_id)
        except Expediente.DoesNotExist:
            return None

    def _crear_solicitud(
        self,
        expediente: Expediente,
        estado: str,
        prioridad: str,
        fecha_registro: datetime,
        observacion: str | None,
        creado_por_id: int,
    ) -> Solicitud:
        """
        Crea una nueva Solicitud en la base de datos.

        Sync — para uso dentro de transaction.atomic.

        Args:
            expediente: Instancia de Expediente asociado.
            estado: Estado inicial de la solicitud.
            prioridad: Prioridad del trámite.
            fecha_registro: Fecha y hora de registro.
            observacion: Observación opcional.
            creado_por_id: ID del usuario que crea la solicitud.

        Returns:
            Instancia de Solicitud creada.
        """
        return Solicitud.objects.create(
            expediente=expediente,
            estado=estado,
            prioridad=prioridad,
            fecha_registro=fecha_registro,
            observacion=observacion,
            creado_por_id=creado_por_id,
        )

    def _crear_historial_estado(
        self,
        solicitud: Solicitud,
        estado_anterior: str | None,
        estado_nuevo: str,
        cambiado_por_id: int,
        fecha_cambio: datetime,
        motivo: str | None = None,
        observacion: str | None = None,
        origen: str | None = None,
    ) -> SolicitudEstadoHistorial:
        """
        Crea un registro de historial de cambio de estado.

        Sync — para uso dentro de transaction.atomic.

        Args:
            solicitud: Instancia de Solicitud.
            estado_anterior: Estado anterior (None si es creación).
            estado_nuevo: Nuevo estado.
            cambiado_por_id: ID del usuario que realiza el cambio.
            fecha_cambio: Fecha real del cambio.
            motivo: Motivo opcional del cambio.
            observacion: Observación opcional.
            origen: Origen del cambio (CREACION, CAMBIO_ESTADO, CIERRE, ANULACION).

        Returns:
            Instancia de SolicitudEstadoHistorial creada.
        """
        return SolicitudEstadoHistorial.objects.create(
            solicitud=solicitud,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            cambiado_por_id=cambiado_por_id,
            fecha_cambio=fecha_cambio,
            motivo=motivo,
            observacion=observacion,
            origen=origen,
        )
