"""
ConversacionController — thin async HTTP controller for conversations API.

Responsabilidades:
- Recibir requests HTTP y delegar al ConversacionOrchestrator.
- Transformar entidades de dominio a schemas HTTP via ConversacionPresenter.
- Authentication via JWT (IsAuthenticated).
- NO lógica de negocio.

Patrón async: controller async → orchestrator async → flujo async → core sync.
"""

from uuid import UUID

from asgiref.sync import sync_to_async
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated
from ninja import Form, Query, File
from ninja.files import UploadedFile
from injector import inject

from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from core.types import DataForm, parse_form_json
from modules.conversaciones.domain.models import Conversacion, Mensaje
from modules.conversaciones.domain.schemas.conversacion_schemas import (
    ConversacionCreateData,
)
from modules.conversaciones.domain.schemas.mensaje_schemas import (
    MensajeArchivoAdjuntoData,
    MensajeCreateData,
    MensajeMencionData,
)
from modules.conversaciones.presentation.presenters.conversacion_presenter import (
    ConversacionPresenter,
)
from modules.conversaciones.presentation.schemas.conversacion_schemas import (
    ArchivoAdjuntoCreateIn,
    ConversacionCerrarIn,
    ConversacionCreateIn,
    ConversacionDetailOut,
    ConversacionOut,
    MencionCreateIn,
    MensajeCreateIn,
    MensajeOut,
)
from modules.conversaciones.domain.services.orchestrators.conversacion_orchestrator import (
    ConversacionOrchestrator,
)
from modules.conversaciones.domain.exceptions import (
    ConversacionCerradaError,
    ConversacionNotFoundError,
    MensajeNotFoundError,
)


@api_controller(
    "/conversaciones",
    tags=["Conversaciones"],
    permissions=[IsAuthenticated],
)
class ConversacionController:
    """
    Controlador HTTP para operaciones de conversación y mensajes.

    Todos los endpoints requieren autenticación JWT.
    Solo crea/consulta conversaciones — los endpoints de mensajes
    van anidados dentro del recurso conversación.
    """

    @inject
    def __init__(self, conversacion_orchestrator: ConversacionOrchestrator):
        self.orchestrator = conversacion_orchestrator

    # ── Conversacion ───────────────────────────────────────────────────────────

    @route.get("/", response={200: ApiResponse[PaginatedData[ConversacionOut]]})
    async def listar_conversaciones(
        self,
        request,
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    ):
        """
        Lista conversaciones del usuario autenticado.

        Incluye conversaciones donde el usuario participó (como creador o con mensajes).
        """
        usuario_id = request.auth.id

        def _query():
            from django.db.models import Q

            qs = (
                Conversacion.objects
                .filter(
                    Q(creada_por_id=usuario_id)
                    | Q(mensajes__autor_usuario_id=usuario_id)
                )
                .distinct()
                .select_related("creada_por")
                .order_by("-fecha_inicio")
            )

            total = qs.count()
            total_pages = max(1, (total + page_size - 1) // page_size)
            offset = (page - 1) * page_size
            items = list(qs[offset:offset + page_size])
            return items, total, page, page_size, total_pages

        items, total, page, page_size, total_pages = await sync_to_async(
            _query, thread_sensitive=True
        )()

        outs = [
            ConversacionPresenter.present_conversacion(conv) for conv in items
        ]

        return success_response(PaginatedData(
            items=outs,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ))

    @route.post("/", response={200: ApiResponse[ConversacionOut]})
    async def crear_conversacion(
        self,
        request,
        data: ConversacionCreateIn,
    ):
        """
        Crea una nueva conversación, opcionalmente vinculada a una Solicitud.

        El usuario autenticado es el creador.
        """
        from modules.conversaciones.domain.schemas.conversacion_schemas import (
            ConversacionCreateData,
        )
        from datetime import datetime, timezone

        user_id = request.auth.id

        create_data = ConversacionCreateData(
            titulo=data.titulo,
            creada_por_id=user_id,
            fecha_inicio=datetime.now(timezone.utc),
        )

        conv = await self.orchestrator.crear_conversacion(
            data=create_data,
            solicitud_id=data.solicitud_id,
        )

        out = ConversacionPresenter.present_conversacion(conv)
        return success_response(out)

    @route.get("/{conversacion_id}", response={200: ApiResponse[ConversacionDetailOut]})
    async def obtener_conversacion(
        self,
        request,
        conversacion_id: UUID,
    ):
        """
        Obtiene el detalle de una conversación con sus mensajes.

        Solo retorna mensajes no eliminados, ordenados por fecha de envío.
        """
        usuario_id = request.auth.id

        def _query():
            try:
                conv = (
                    Conversacion.objects
                    .select_related("creada_por")
                    .get(id=conversacion_id)
                )
                mensajes = (
                    Mensaje.objects
                    .filter(conversacion_id=conversacion_id, eliminado_at__isnull=True)
                    .select_related("autor_usuario")
                    .prefetch_related("archivos_adjuntos", "menciones")
                    .order_by("fecha_envio")
                )
                return conv, list(mensajes)
            except Conversacion.DoesNotExist:
                return None, None

        result = await sync_to_async(_query, thread_sensitive=True)()
        if result[0] is None:
            from ninja.errors import HttpError
            raise HttpError(404, "Conversación no encontrada")

        conv, mensajes = result
        out = ConversacionPresenter.present_conversacion_detail(conv, mensajes)
        return success_response(out)

    @route.post("/{conversacion_id}/cerrar", response={200: ApiResponse[ConversacionOut]})
    async def cerrar_conversacion(
        self,
        request,
        conversacion_id: UUID,
    ):
        """
        Cierra una conversación.

        Solo el creador o un participante puede cerrar una conversación abierta.
        Operación idempotente — cerrar dos veces no cambia nada.
        """
        usuario_id = request.auth.id

        try:
            conv = await self.orchestrator.cerrar_conversacion(
                conversacion_id=conversacion_id,
                cerrado_por_id=usuario_id,
            )
        except ConversacionNotFoundError:
            from ninja.errors import HttpError
            raise HttpError(404, "Conversación no encontrada")

        out = ConversacionPresenter.present_conversacion(conv)
        return success_response(out)

    # ── Mensaje ───────────────────────────────────────────────────────────────

    @route.post("/{conversacion_id}/mensajes", response={200: ApiResponse[MensajeOut]})
    async def crear_mensaje(
        self,
        request,
        conversacion_id: UUID,
        data: Form[DataForm],
        files: File[list[UploadedFile]] = [],
    ):
        """
        Publica un nuevo mensaje en una conversación.

        El usuario autenticado es el autor.
        La conversación debe estar abierta.

        Patrón dual payload (FormData + archivos) — estándar del proyecto:
        - data: JSON string con los campos del mensaje (serializado como DataForm)
        - files: lista de archivos con nombre con formato "token___nombre_real.ext"

        El token se usa para hidratar los campos UploadedFile en el schema.
        """
        payload = parse_form_json(data.data, files, MensajeCreateIn)

        usuario_id = request.auth.id

        # Build domain schema from HTTP schema
        adjuntos = [
            MensajeArchivoAdjuntoData(
                nombre_original=adj.nombre_original,
                mime_type=adj.mime_type,
                tamano_bytes=adj.tamano_bytes,
                archivo=getattr(adj, 'archivo', None),
                subido_por_id=usuario_id,
                descripcion=getattr(adj, 'descripcion', None),
            )
            for adj in (payload.archivos_adjuntos or [])
        ]
        menciones = [
            MensajeMencionData(usuario_id=men.usuario_id)
            for men in (payload.menciones or [])
        ]

        msg_data = MensajeCreateData(
            conversacion_id=conversacion_id,
            autor_usuario_id=usuario_id,
            contenido=payload.contenido,
            archivos_adjuntos=adjuntos,
            menciones=menciones,
            mensaje_padre_id=payload.mensaje_padre_id,
        )

        try:
            msg = await self.orchestrator.crear_mensaje(data=msg_data)
        except ConversacionCerradaError:
            from ninja.errors import HttpError
            raise HttpError(400, "No se puede enviar mensajes a una conversación cerrada")

        # Prefetch related data before presenting (presenter is sync, must not hit ORM)
        msg = await sync_to_async(
            lambda: Mensaje.objects.prefetch_related(
                "archivos_adjuntos", "menciones"
            ).get(id=msg.id)
        )()

        out = ConversacionPresenter.present_mensaje(msg)
        return success_response(out)

    @route.delete(
        "/mensajes/{mensaje_id}",
        response={200: ApiResponse[MensajeOut]},
    )
    async def eliminar_mensaje(
        self,
        request,
        mensaje_id: UUID,
    ):
        """
        Elimina (soft-delete) un mensaje.

        El usuario autenticado debe ser el autor del mensaje.
        Operación idempotente — eliminar dos veces no cambia nada.
        """
        usuario_id = request.auth.id

        try:
            msg = await self.orchestrator.eliminar_mensaje(
                mensaje_id=mensaje_id,
                eliminado_por_id=usuario_id,
            )
        except MensajeNotFoundError:
            from ninja.errors import HttpError
            raise HttpError(404, "Mensaje no encontrado")

        # Prefetch related data before presenting (presenter is sync, must not hit ORM)
        msg = await sync_to_async(
            lambda: Mensaje.objects.prefetch_related(
                "archivos_adjuntos", "menciones"
            ).get(id=msg.id)
        )()

        out = ConversacionPresenter.present_mensaje(msg)
        return success_response(out)
