"""
NotificacionController — controlador HTTP ligero para consulta y interacción con notificaciones.

Filtra por el usuario autenticado y su participación en áreas.
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
import math
from uuid import UUID

from asgiref.sync import sync_to_async
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated
from ninja import Query
from injector import inject

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.notificaciones.presentation.schemas.notificacion_schemas import (
    NotificacionListItemOut,
    NotificacionDetalleOut,
    NotificacionDetailOut,
    NotificacionResumenOut,
)
from modules.notificaciones.domain.models import Notificacion, NotificacionUsuario
from modules.notificaciones.domain.selectors.notificacion_selector import NotificacionSelector
from modules.notificaciones.presentation.presenters.notificacion_presenter import NotificacionPresenter
from modules.notificaciones.domain.services.orchestrators.notificacion_orchestrator import (
    NotificacionOrchestrator,
)


@api_controller("/notificaciones", tags=["Notificaciones"], permissions=[IsAuthenticated])
class NotificacionController:
    """
    Controlador para consulta e interacción con notificaciones individualizadas.

    Filtra por el usuario autenticado según su participación en áreas.
    Incluye endpoints de lectura y de marcado de interacción (vista, descarte).
    """

    @inject
    def __init__(self, notificacion_orchestrator: NotificacionOrchestrator):
        self.notificacion_orchestrator = notificacion_orchestrator

    @route.get("/", response={200: ApiResponse[PaginatedData[NotificacionListItemOut]]})
    async def listar_notificaciones(
        self,
        request,
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
    ):
        """
        Lista notificaciones del usuario autenticado.

        Filtra por el usuario ve notificaciones de las áreas donde participa o es miembro.
        El estado individual de cada notificación se derive de NotificacionUsuario.
        """
        usuario_id = request.auth.id

        def _query():
            from django.db.models import Prefetch

            # Prefetch solo las interacciones del usuario actual
            mis_interacciones = NotificacionUsuario.objects.filter(usuario_id=usuario_id)

            # Notificaciones donde el usuario está en NotificacionUsuario
            qs = (
                Notificacion.objects
                .filter(usuarios_notificados__usuario_id=usuario_id)
                .prefetch_related(
                    Prefetch("usuarios_notificados", queryset=mis_interacciones),
                    Prefetch("areas_notificadas__area"),
                    Prefetch(
                        "contexto_solicitud__solicitud__expediente",
                    ),
                    Prefetch("contexto_solicitud__periodo"),
                )
                .order_by("-ocurrido_en", "-created_at")
            )

            total = qs.count()
            total_pages = math.ceil(total / page_size) if total > 0 else 1
            offset = (page - 1) * page_size
            items = list(qs[offset:offset + page_size])

            return items, total, page, page_size, total_pages

        items, total, page, page_size, total_pages = await sync_to_async(_query, thread_sensitive=True)()

        # Presentación via presenter (evita lógica de presentación inline en controller)
        # Must run in sync thread since presenter accesses prefetched relations
        item_outs = await sync_to_async(
            lambda: [
                NotificacionPresenter.present_list_item(notif, usuario_id)
                for notif in items
            ],
            thread_sensitive=True,
        )()

        return success_response(PaginatedData(
            items=item_outs,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ))

    @route.get("/resumen", response={200: ApiResponse[NotificacionResumenOut]})
    async def obtener_resumen(self, request):
        """
        Retorna contadores agregados de notificaciones para el usuario autenticado.

        Todos los conteos se basan en la tabla NotificacionUsuario filtrada por
        request.auth.id.

        semantics:
        - total: todas las notificaciones del usuario (NotificacionUsuario)
        - no_vistas: vista_at IS NULL AND abierta_at IS NULL AND descartada_at IS NULL
        - vistas: vista_at NOT NULL AND abierta_at IS NULL AND descartada_at IS NULL
        - abiertas: abierta_at NOT NULL AND descartada_at IS NULL
        - descartadas: descartada_at NOT NULL
        - sin_leer: alias de no_vistas (compatibilidad con frontend)
        """
        from django.db.models import Count, Q, F

        usuario_id = request.auth.id

        def _query():
            qs = NotificacionUsuario.objects.filter(usuario_id=usuario_id)

            total = qs.count()
            no_vistas = qs.filter(
                vista_at__isnull=True,
                abierta_at__isnull=True,
                descartada_at__isnull=True,
            ).count()
            vistas = qs.filter(
                vista_at__isnull=False,
                abierta_at__isnull=True,
                descartada_at__isnull=True,
            ).count()
            abiertas = qs.filter(
                abierta_at__isnull=False,
                descartada_at__isnull=True,
            ).count()
            descartadas = qs.filter(descartada_at__isnull=False).count()

            return total, no_vistas, vistas, abiertas, descartadas

        total, no_vistas, vistas, abiertas, descartadas = await sync_to_async(
            _query, thread_sensitive=True
        )()

        return success_response(NotificacionResumenOut(
            total=total,
            no_vistas=no_vistas,
            vistas=vistas,
            abiertas=abiertas,
            descartadas=descartadas,
            sin_leer=no_vistas,  # frontend compatibility alias
        ))

    @route.get("/{notificacion_id}/detalle", response={200: ApiResponse[NotificacionDetalleOut]})
    async def obtener_notificacion_detalle(
        self,
        request,
        notificacion_id: UUID,
    ):
        """
        Obtiene el detalle de una notificación con contexto restructurado.

        NUEVO endpoint — retorna NotificacionDetalleOut con expediente y período
        como objetos anidados (expediente_publico, periodo) en lugar de campos planos.

        Soporta ambos ámbitos:
        - SOLICITUD: contexto completo con expediente y período anidados
        - SISTEMA: contexto base (expediente_publico=None, periodo=None)

        Este es el endpoint consumido por el frontend para la página de detalle.
        """
        from ninja.errors import HttpError

        usuario_id = request.auth.id

        notif = await sync_to_async(
            NotificacionSelector.obtener_detalle,
            thread_sensitive=True,
        )(notificacion_id, usuario_id)

        if notif is None:
            raise HttpError(404, "Notificación no encontrada")

        # Must run in sync thread since presenter accesses prefetched relations
        detail_out = await sync_to_async(
            lambda: NotificacionPresenter.present_detail_contextual(notif, usuario_id),
            thread_sensitive=True,
        )()

        return success_response(detail_out)

    @route.get("/{notificacion_id}", response={200: ApiResponse[NotificacionDetailOut]})
    async def obtener_notificacion(
        self,
        request,
        notificacion_id: UUID,
    ):
        """
        Obtiene el detalle de una notificación.

        Incluye contexto (solicitud, expediente, área, período) e
        interacciones del actor actual.
        """
        from ninja.errors import HttpError

        usuario_id = request.auth.id

        def _query():
            from django.db.models import Prefetch

            try:
                return (
                    Notificacion.objects
                    .select_related(
                        "generada_por",
                    )
                    .prefetch_related(
                        "usuarios_notificados__usuario",
                        "areas_notificadas__area",
                        Prefetch(
                            "contexto_solicitud__solicitud__expediente",
                        ),
                        Prefetch("contexto_solicitud__periodo"),
                    )
                    .get(id=notificacion_id)
                )
            except Notificacion.DoesNotExist:
                return None

        notif = await sync_to_async(_query, thread_sensitive=True)()

        if notif is None:
            raise HttpError(404, "Notificación no encontrada")

        # Must run in sync thread since present_detail accesses prefetched relations
        detail_out = await sync_to_async(
            lambda: NotificacionPresenter.present_detail(notif, usuario_id),
            thread_sensitive=True,
        )()

        return success_response(detail_out)

    @route.post("/{notificacion_id}/vista", response={200: ApiResponse[NotificacionDetailOut]})
    async def marcar_vista(
        self,
        request,
        notificacion_id: UUID,
    ):
        """
        Marca una notificación como vista para el usuario autenticado.

        Idempotente: si ya fue marcada, no cambia el timestamp existente.
        """
        notif = await self.notificacion_orchestrator.marcar_vista(
            notificacion_id=notificacion_id,
            usuario_id=request.auth.id,
        )

        # Must run in sync thread since present_detail accesses prefetched relations
        detail_out = await sync_to_async(
            lambda: NotificacionPresenter.present_detail(notif, request.auth.id),
            thread_sensitive=True,
        )()
        return success_response(detail_out)

    @route.post("/{notificacion_id}/abrir", response={200: ApiResponse[NotificacionDetailOut]})
    async def abrir_notificacion(
        self,
        request,
        notificacion_id: UUID,
    ):
        """
        Marca una notificación como abierta para el usuario autenticado.

        Idempotente: si ya fue abierta, no cambia el timestamp existente.
        """
        notif = await self.notificacion_orchestrator.abrir(
            notificacion_id=notificacion_id,
            usuario_id=request.auth.id,
        )

        # Must run in sync thread since present_detail accesses prefetched relations
        detail_out = await sync_to_async(
            lambda: NotificacionPresenter.present_detail(notif, request.auth.id),
            thread_sensitive=True,
        )()
        return success_response(detail_out)

    @route.post("/{notificacion_id}/descartar", response={200: ApiResponse[NotificacionDetailOut]})
    async def descartar_notificacion(
        self,
        request,
        notificacion_id: UUID,
    ):
        """
        Descarta una notificación para el usuario autenticado.

        Idempotente: si ya fue descartada, no cambia el timestamp existente.
        """
        notif = await self.notificacion_orchestrator.descartar(
            notificacion_id=notificacion_id,
            usuario_id=request.auth.id,
        )

        # Must run in sync thread since present_detail accesses prefetched relations
        detail_out = await sync_to_async(
            lambda: NotificacionPresenter.present_detail(notif, request.auth.id),
            thread_sensitive=True,
        )()
        return success_response(detail_out)
