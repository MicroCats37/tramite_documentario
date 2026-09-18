"""
SolicitudOrchestrator — fachada asíncrona ligera para controladores de Solicitud.

Delegación de creación a SolicitudCreacionFlujo.
Consultas directas para lectura (listar, obtener, estado_operativo).
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
import math
from uuid import UUID
from datetime import datetime

from asgiref.sync import sync_to_async
from django.db.models import Q
from injector import inject

from modules.tramites.domain.models import Solicitud
from modules.asignaciones.domain.constants import EstadoPeriodo, EstadoRespuesta
from modules.tramites.domain.constants import EstadoSolicitud
from modules.tramites.presentation.schemas.solicitud_in import (
    SolicitudCreateIn,
    SolicitudHibridaCreateIn,
)
from modules.tramites.domain.services.flujos.solicitud_flujo import (
    SolicitudCreacionFlujo,
    SolicitudAreaOperacionesFlujo,
)


class SolicitudOrchestrator:
    """
    Fachada asíncrona ligera — delega creación a SolicitudCreacionFlujo,
    operaciones de área a SolicitudAreaOperacionesFlujo,
    y consultas directas para lectura.
    """

    @inject
    def __init__(
        self,
        flujo: SolicitudCreacionFlujo,
        area_operaciones_flujo: SolicitudAreaOperacionesFlujo,
    ):
        self.flujo = flujo
        self.area_operaciones_flujo = area_operaciones_flujo

    async def crear_solicitud_con_distribucion(
        self,
        payload: SolicitudCreateIn,
        usuario_id: int,
    ) -> Solicitud:
        """
        Crea una nueva solicitud con distribución de áreas.
        """
        return await self.flujo._proceso_crear_solicitud(payload, usuario_id)

    async def crear_solicitud_hibrida(
        self,
        payload: SolicitudHibridaCreateIn,
        usuario_id: int,
    ) -> Solicitud:
        """
        Crea una solicitud con expediente y distribución en una sola operación.
        """
        return await self.flujo._proceso_crear_hibrido(payload, usuario_id)

    async def listar_solicitudes(
        self,
        page: int = 1,
        page_size: int = 10,
        estado: str | None = None,
        prioridad: str | None = None,
        area_id: UUID | None = None,
        tipo_participacion: str | None = None,
        periodo_estado: str | None = None,
        usuario_id: int | None = None,
        me: bool = False,
        mis_areas: bool = False,
        solo_principal: bool = False,
        creadas_por_mi: bool = False,
        sin_participantes: bool = False,
        con_respuesta: bool = False,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
        busqueda: str | None = None,
    ) -> tuple:
        """
        Lista solicitudes con filtros y paginación.

        Args:
            page: Número de página (1-indexed)
            page_size: Tamaño de página (max 100)
            estado: Filtrar por estado
            prioridad: Filtrar por prioridad
            area_id: Filtrar por área asignada
            tipo_participacion: Filtrar por tipo de participación
            periodo_estado: Filtrar por estado de período
            usuario_id: Filtrar por usuario asignado
            me: Si True, filtra por solicitudes donde request.user.id participa
            mis_areas: Si True, filtra solicitudes con área asignada vigente donde el usuario tiene asignación activa
            solo_principal: Si True (solo con mis_areas=True), filtra solo áreas PRINCIPAL en período activo
            creadas_por_mi: Si True, filtra solicitudes creadas por el usuario autenticado
            sin_participantes: Si True, filtra asignaciones sin participantes activos
            con_respuesta: Si True, filtra áreas con respuesta emitida
            fecha_desde: Filtrar por fecha de registro >= fecha_desde
            fecha_hasta: Filtrar por fecha de registro <= fecha_hasta
            busqueda: Busca en id_publico del expediente, numero_documento, dni, asunto

        Returns:
            Tupla (items, total, page, page_size, total_pages)
        """
        def _query():
            qs = (
                Solicitud.objects
                .select_related("expediente", "creado_por")
                .prefetch_related(
                    "asignaciones__area",
                    "asignaciones__periodos",
                )
                .order_by("-fecha_registro")
            )

            if estado:
                qs = qs.filter(estado=estado)
            if prioridad:
                qs = qs.filter(prioridad=prioridad)
            if fecha_desde:
                qs = qs.filter(fecha_registro__gte=fecha_desde)
            if fecha_hasta:
                qs = qs.filter(fecha_registro__lte=fecha_hasta)
            if busqueda:
                qs = qs.filter(
                    Q(expediente__id_publico__icontains=busqueda)
                    | Q(expediente__numero_documento__icontains=busqueda)
                    | Q(expediente__dni__icontains=busqueda)
                    | Q(expediente__asunto__icontains=busqueda)
                )

            if area_id:
                qs = qs.filter(asignaciones__area_id=area_id)

            if tipo_participacion:
                qs = qs.filter(asignaciones__periodos__tipo_participacion=tipo_participacion)

            if periodo_estado:
                qs = qs.filter(asignaciones__periodos__estado=periodo_estado)

            if me and usuario_id:
                qs = qs.filter(
                    asignaciones__periodos__usuarios__usuario_id=usuario_id,
                    asignaciones__periodos__usuarios__fecha_fin__isnull=True,
                )

            if creadas_por_mi and usuario_id:
                qs = qs.filter(creado_por_id=usuario_id)

            if sin_participantes:
                qs = qs.filter(
                    asignaciones__periodos__usuarios__isnull=True,
                )

            if con_respuesta:
                qs = qs.filter(
                    asignaciones__periodos__respuestas__estado=EstadoRespuesta.EMITIDA,
                )

            if mis_areas and usuario_id:
                # Get user's currently assigned areas (active assignments with no end date)
                from modules.usuarios.domain.models import AsignacionUsuario
                from modules.asignaciones.domain.models import SolicitudAsignacion
                from modules.asignaciones.domain.models import SolicitudAsignacionPeriodo
                user_area_ids = list(
                    AsignacionUsuario.objects.vigentes()
                    .filter(usuario_id=usuario_id)
                    .values_list("area_id", flat=True)
                )
                if user_area_ids:
                    if solo_principal:
                        # Both conditions (active period AND PRINCIPAL) must be true
                        # for the SAME period - use a subquery that checks this
                        qs = qs.filter(
                            asignaciones__area_id__in=user_area_ids,
                        ).filter(
                            asignaciones__periodos__fecha_fin__isnull=True,
                            asignaciones__periodos__tipo_participacion="PRINCIPAL",
                        )
                    else:
                        qs = qs.filter(
                            asignaciones__area_id__in=user_area_ids,
                            asignaciones__periodos__fecha_fin__isnull=True,
                        )
                else:
                    # User has no active area assignments → return empty result
                    qs = qs.none()

            qs = qs.distinct()

            total = qs.count()
            total_pages = math.ceil(total / page_size) if total > 0 else 1
            offset = (page - 1) * page_size
            items = list(qs[offset:offset + page_size])

            return items, total, page, page_size, total_pages

        return await sync_to_async(_query, thread_sensitive=True)()

    def obtener_solicitud_sync(self, solicitud_id: UUID) -> Solicitud | None:
        """
        Versión síncrona de obtener_solicitud para usar desde controllers async
        vía sync_to_async.

        Args:
            solicitud_id: UUID de la solicitud

        Returns:
            Solicitud con expediente, asignaciones, períodos, etc. o None
        """
        try:
            return (
                Solicitud.objects
                .select_related("expediente", "creado_por", "expediente__tipo_documento")
                .prefetch_related(
                    "expediente__archivos",
                    "expediente__antecedentes_vinculados__antecedente",
                    "asignaciones__area",
                    "asignaciones__periodos__usuarios__usuario",
                    "asignaciones__periodos__respuestas",
                    "asignaciones__periodos__historial_estados",
                    "historial_estados__cambiado_por",
                    "conversacionpuente__conversacion",
                )
                .get(id=solicitud_id)
            )
        except Solicitud.DoesNotExist:
            return None

    async def calcular_estado_operativo(self, solicitud_id: UUID) -> dict | None:
        """
        Calcula el resumen operativo sin persistir nada.

        Args:
            solicitud_id: UUID de la solicitud

        Returns:
            dict con total_areas, areas_pendientes, areas_en_gestion,
            areas_cerradas, con_respuesta, sin_participantes, vencida
            o None si la solicitud no existe
        """
        def _query():
            try:
                solicitud = (
                    Solicitud.objects
                    .prefetch_related(
                        "asignaciones__periodos__usuarios",
                        "asignaciones__periodos__respuestas",
                    )
                    .get(id=solicitud_id)
                )
            except Solicitud.DoesNotExist:
                return None

            total_areas = solicitud.asignaciones.count()
            areas_pendientes = 0
            areas_en_gestion = 0
            areas_cerradas = 0
            con_respuesta = 0
            sin_participantes = 0

            for asignacion in solicitud.asignaciones.all():
                periodos = list(asignacion.periodos.all())
                if not periodos:
                    continue

                ultimo = max(periodos, key=lambda p: p.numero_ciclo)

                todos_cerrados = all(p.fecha_fin is not None for p in periodos)
                if todos_cerrados:
                    areas_cerradas += 1
                elif ultimo.estado == EstadoPeriodo.PENDIENTE:
                    areas_pendientes += 1
                elif ultimo.estado == EstadoPeriodo.EN_GESTION:
                    areas_en_gestion += 1

                tiene_respuesta = any(
                    r.estado == EstadoRespuesta.EMITIDA for p in periodos for r in p.respuestas.all()
                )
                if tiene_respuesta:
                    con_respuesta += 1

                tiene_participante = any(
                    u.fecha_fin is None for p in periodos for u in p.usuarios.all()
                )
                if not tiene_participante:
                    sin_participantes += 1

            from django.utils import timezone as djtz
            now = djtz.now()
            vencida = (
                solicitud.fecha_limite is not None
                and solicitud.fecha_limite < now
                and solicitud.estado != EstadoSolicitud.FINALIZADA
            )

            return {
                "total_areas": total_areas,
                "areas_pendientes": areas_pendientes,
                "areas_en_gestion": areas_en_gestion,
                "areas_cerradas": areas_cerradas,
                "con_respuesta": con_respuesta,
                "sin_participantes": sin_participantes,
                "vencida": vencida,
            }

        return await sync_to_async(_query, thread_sensitive=True)()

    async def incorporar_area(
        self,
        solicitud_id: UUID,
        area_id: UUID,
        tipo_participacion: str,
        observacion: str | None,
        usuario_id: int,
    ):
        """
        Incorpora un área a una solicitud existente.

        Args:
            solicitud_id: UUID de la Solicitud.
            area_id: UUID del Área a incorporar.
            tipo_participacion: PRINCIPAL o ADJUNTA.
            observacion: Observación opcional.
            usuario_id: ID del usuario que realiza la operación.

        Returns:
            Instancia de Solicitud actualizada.
        """
        return await self.area_operaciones_flujo._proceso_incorporar_area(
            solicitud_id=solicitud_id,
            area_id=area_id,
            tipo_participacion=tipo_participacion,
            observacion=observacion,
            usuario_id=usuario_id,
        )

    def obtener_trazabilidad_sync(self, solicitud_id: UUID) -> Solicitud | None:
        """
        Carga el grafo completo de trazabilidad para una solicitud.

        Carga todas las asignaciones con sus períodos ordenados por ciclo,
        participantes, respuestas y historiales de estado.

        Args:
            solicitud_id: UUID de la solicitud

        Returns:
            Solicitud con el grafo completo eager-loaded, o None si no existe
        """
        try:
            from django.db.models import Prefetch

            from modules.asignaciones.domain.models import (
                SolicitudAsignacionPeriodo,
                SolicitudAsignacionUsuario,
                SolicitudAsignacionRespuesta,
                SolicitudAsignacionPeriodoEstadoHistorial,
            )

            # Prefetch para periodos con ordenamiento por numero_ciclo
            periodos_prefetch = Prefetch(
                "asignaciones__periodos",
                queryset=SolicitudAsignacionPeriodo.objects.select_related(
                    "iniciado_por",
                    "finalizado_por",
                ).prefetch_related(
                    Prefetch(
                        "usuarios",
                        queryset=SolicitudAsignacionUsuario.objects.select_related(
                            "usuario",
                            "asignado_por",
                            "retirado_por",
                        ),
                    ),
                    Prefetch(
                        "respuestas",
                        queryset=SolicitudAsignacionRespuesta.objects.select_related(
                            "emitido_por",
                        ),
                    ),
                    Prefetch(
                        "historial_estados",
                        queryset=SolicitudAsignacionPeriodoEstadoHistorial.objects.select_related(
                            "cambiado_por",
                        ).order_by("fecha_cambio"),
                    ),
                ).order_by("numero_ciclo"),
            )

            return (
                Solicitud.objects
                .select_related("expediente")
                .prefetch_related(
                    "historial_estados__cambiado_por",
                    periodos_prefetch,
                )
                .get(id=solicitud_id)
            )
        except Solicitud.DoesNotExist:
            return None