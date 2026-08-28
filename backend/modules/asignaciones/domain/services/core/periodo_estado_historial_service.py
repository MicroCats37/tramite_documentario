"""
PeriodoEstadoHistorialCoreService — operaciones sync para el historial de estados del período.

NO usa transaction.atomic() internamente — el flujo que lo llama provee la
transacción atómica cuando necesita modificar el período junto con su historial.
"""

from datetime import datetime

from injector import inject

from modules.asignaciones.domain.models import (
    SolicitudAsignacionPeriodo,
    SolicitudAsignacionPeriodoEstadoHistorial,
)
from modules.asignaciones.domain.constants import (
    EstadoPeriodoOperativo,
    OrigenEstadoPeriodo,
)
from modules.usuarios.domain.models import Usuario


class PeriodoEstadoHistorialCoreService:
    """
    Operaciones síncronas para SolicitudAsignacionPeriodoEstadoHistorial.

    Toda operación es sync y no abre transaction.atomic() internamente.
    El flujo que la调用 provee la atomicidad si es necesaria.
    """

    def registrar_transicion(
        self,
        periodo: SolicitudAsignacionPeriodo,
        estado_nuevo: str,
        fecha_cambio: datetime,
        cambiado_por: Usuario | None = None,
        estado_anterior: str | None = None,
        motivo: str | None = None,
        origen: str | None = None,
    ) -> SolicitudAsignacionPeriodoEstadoHistorial:
        """
        Registra una transición de estado para el período.

        Sync — para uso dentro de transaction.atomic.

        Args:
            periodo: Instancia de SolicitudAsignacionPeriodo.
            estado_nuevo: Nuevo estado operativo (PENDIENTE, EN_GESTION, CERRADO).
            fecha_cambio: Fecha real del cambio (puede ser histórica).
            cambiado_por: Usuario que ejecutó la transición (nullable para sistema/Legacy).
            estado_anterior: Estado previo (nullable para primer registro/creación).
            motivo: Razón opcional del cambio.
            origen: Origen de la transición (CREACION, AUTOASIGNACION, CIERRE, etc.).

        Returns:
            Instancia de SolicitudAsignacionPeriodoEstadoHistorial creada.
        """
        return SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            fecha_cambio=fecha_cambio,
            cambiado_por=cambiado_por,
            motivo=motivo,
            origen=origen,
        )

    def crear_historial_inicial(
        self,
        periodo: SolicitudAsignacionPeriodo,
        fecha_inicio: datetime,
        iniciado_por: Usuario | None = None,
    ) -> SolicitudAsignacionPeriodoEstadoHistorial:
        """
        Crea el registro inicial de historial al abrir un nuevo período.

        El estado inicial es siempre PENDIENTE con origen CREACION.

        Sync — para uso dentro de transaction.atomic.

        Args:
            periodo: Instancia de SolicitudAsignacionPeriodo.
            fecha_inicio: Fecha de inicio del período.
            iniciado_por: Usuario que inició el período (nullable para Legacy).

        Returns:
            Instancia de SolicitudAsignacionPeriodoEstadoHistorial creada.
        """
        return self.registrar_transicion(
            periodo=periodo,
            estado_anterior=None,
            estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
            fecha_cambio=fecha_inicio,
            cambiado_por=iniciado_por,
            motivo=None,
            origen=OrigenEstadoPeriodo.CREACION,
        )
