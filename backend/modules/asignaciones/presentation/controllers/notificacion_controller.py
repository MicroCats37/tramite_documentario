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
from modules.asignaciones.presentation.schemas.notificacion_schemas import (
    NotificacionItemOut,
    NotificacionDetailOut,
)
from modules.asignaciones.domain.models import Notificacion, NotificacionUsuario
from modules.asignaciones.presentation.presenters.notificacion_presenter import NotificacionPresenter
from modules.asignaciones.domain.services.orchestrators.notificacion_orchestrator import (
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

    @route.get("/", response={200: ApiResponse[PaginatedData[NotificacionItemOut]]})
    async def listar_notificaciones(
        self,
        request,
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
        estado: str | None = Query(None, description="Filtrar por estado de notificación"),
    ):
        """
        Lista notificaciones del usuario autenticado.

        Filtra por:
        - estado: PENDIENTE, ENVIADA, LEIDA, DESCARTADA
        - El usuario ve notificaciones de las áreas donde participa o es miembro
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
                .select_related("area", "solicitud", "solicitud__expediente")
                .prefetch_related(
                    Prefetch("usuarios_notificados", queryset=mis_interacciones)
                )
                .order_by("-fecha_evento", "-created_at")
            )

            if estado:
                qs = qs.filter(estado=estado)

            total = qs.count()
            total_pages = math.ceil(total / page_size) if total > 0 else 1
            offset = (page - 1) * page_size
            items = list(qs[offset:offset + page_size])

            return items, total, page, page_size, total_pages

        items, total, page, page_size, total_pages = await sync_to_async(_query, thread_sensitive=True)()

        # Presentación via presenter (evita lógica de presentación inline en controller)
        item_outs = [
            NotificacionPresenter.present_list_item(notif, usuario_id)
            for notif in items
        ]

        return success_response(PaginatedData(
            items=item_outs,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ))

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
            try:
                return (
                    Notificacion.objects
                    .select_related(
                        "area",
                        "solicitud__expediente",
                        "generada_por",
                        "periodo__asignacion__area",
                    )
                    .prefetch_related("usuarios_notificados__usuario")
                    .get(id=notificacion_id)
                )
            except Notificacion.DoesNotExist:
                return None

        notif = await sync_to_async(_query, thread_sensitive=True)()

        if notif is None:
            raise HttpError(404, "Notificación no encontrada")

        # Presentación via presenter (evita lógica de presentación inline en controller)
        detail_out = await NotificacionPresenter.present_detail(notif, usuario_id)

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

        detail_out = await NotificacionPresenter.present_detail(notif, request.auth.id)
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

        detail_out = await NotificacionPresenter.present_detail(notif, request.auth.id)
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

        detail_out = await NotificacionPresenter.present_detail(notif, request.auth.id)
        return success_response(detail_out)
