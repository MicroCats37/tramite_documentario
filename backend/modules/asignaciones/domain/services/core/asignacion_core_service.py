"""
AsignacionCoreService — operaciones ORM síncronas para asignaciones.

NO usa transaction.atomic() internamente — el flujo (flujo) provee la
transacción atómica cuando necesita crear asignaciones junto con períodos.
"""
from datetime import datetime

from injector import inject

from modules.asignaciones.domain.models import (
    SolicitudAsignacion,
    SolicitudAsignacionPeriodo,
)
from modules.asignaciones.domain.constants import TipoParticipacion, EstadoPeriodo
from modules.tramites.domain.models import Solicitud
from modules.usuarios.domain.models import Area


class AsignacionCoreService:
    """
    Operaciones síncronas para SolicitudAsignacion y SolicitudAsignacionPeriodo.

    Toda operación es sync y no abre transaction.atomic() internamente.
    El flujo que la调用 provee la atomicidad si es necesaria.
    """

    def _crear_asignacion_con_periodo_inicial(
        self,
        solicitud: Solicitud,
        area: Area,
        tipo_participacion: str,
        observacion: str | None,
        incorporado_por_id: int,
        fecha_incorporacion: datetime,
        numero_ciclo: int,
        estado_periodo: str,
        fecha_inicio: datetime,
        iniciado_por_id: int,
    ) -> SolicitudAsignacion:
        """
        Crea una SolicitudAsignacion junto con su primer SolicitudAsignacionPeriodo.

        También crea el registro inicial de SolicitudAsignacionPeriodoEstadoHistorial
        con estado_anterior=NULL, estado_nuevo=PENDIENTE, origen=CREACION.

        Sync — para uso dentro de transaction.atomic.

        Args:
            solicitud: Instancia de Solicitud.
            area: Instancia de Area.
            tipo_participacion: Tipo de participación (PRINCIPAL o ADJUNTA).
            observacion: Observación opcional.
            incorporado_por_id: ID del usuario que incorpora el área.
            fecha_incorporacion: Fecha de incorporación.
            numero_ciclo: Número de ciclo (1 para inicial).
            estado_periodo: Estado del período inicial (PENDIENTE).
            fecha_inicio: Fecha de inicio del período.
            iniciado_por_id: ID del usuario que inicia el período.

        Returns:
            Tupla (SolicitudAsignacion, SolicitudAsignacionPeriodo) creadas.
        """
        from modules.asignaciones.domain.models.periodo_estado_historial import (
            SolicitudAsignacionPeriodoEstadoHistorial,
        )
        from modules.asignaciones.domain.constants import EstadoPeriodoOperativo, OrigenEstadoPeriodo

        # Crear la asignación (tipo_participacion vive en SolicitudAsignacionPeriodo)
        asignacion = SolicitudAsignacion.objects.create(
            solicitud=solicitud,
            area=area,
            fecha_incorporacion=fecha_incorporacion,
            incorporado_por_id=incorporado_por_id,
            observacion=observacion,
        )

        # Crear el primer período
        periodo = SolicitudAsignacionPeriodo.objects.create(
            asignacion=asignacion,
            numero_ciclo=numero_ciclo,
            tipo_participacion=tipo_participacion,
            estado=estado_periodo,
            fecha_inicio=fecha_inicio,
            iniciado_por_id=iniciado_por_id,
        )

        # Crear el historial inicial del período (estado_anterior=NULL, nuevo=PENDIENTE)
        SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=None,
            estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
            fecha_cambio=fecha_inicio,
            cambiado_por_id=iniciado_por_id,
            origen=OrigenEstadoPeriodo.CREACION,
        )

        return asignacion, periodo
