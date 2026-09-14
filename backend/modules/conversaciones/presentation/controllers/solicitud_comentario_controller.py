"""
SolicitudComentarioController — thin async HTTP controller for contextual solicitud comments.

Responsabilidades:
- Recibir requests HTTP y delegar al SolicitudComentarioOrchestrator.
- Transformar entidades de dominio a schemas HTTP via ConversacionPresenter.
- Authentication via JWT (IsAuthenticated).
- Validar el puente SolicitudConversacion.
- NO lógica de negocio.

Patrón async: controller async → orchestrator async → flujo async → core sync.
"""

from uuid import UUID

from asgiref.sync import sync_to_async
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated
from ninja import Form, File
from ninja.files import UploadedFile
from injector import inject

from core.responses import ApiResponse, success_response
from core.types import DataForm, parse_form_json
from modules.conversaciones.domain.exceptions import (
    BridgeValidationError,
    ConversacionCerradaError,
)
from modules.conversaciones.domain.models import Mensaje
from modules.conversaciones.domain.schemas.mensaje_schemas import (
    MensajeArchivoAdjuntoData,
    MensajeCreateData,
    MensajeMencionData,
)
from modules.conversaciones.domain.services.orchestrators.solicitud_comentario_orchestrator import (
    SolicitudComentarioOrchestrator,
)
from modules.conversaciones.presentation.presenters.conversacion_presenter import (
    ConversacionPresenter,
)
from modules.conversaciones.presentation.schemas.conversacion_schemas import (
    MensajeCreateIn,
    MensajeOut,
)


@api_controller(
    "/solicitudes",
    tags=["Solicitudes", "Comentarios"],
    permissions=[IsAuthenticated],
)
class SolicitudComentarioController:
    """
    Controlador HTTP para operaciones de comentarios contextuales en solicitudes.

    Este controlador es específico para el flujo de comentarios de solicitudes:
    - Valida que la conversación pertenece a la solicitud (bridge check).
    - Crea mensajes con archivos adjuntos y menciones.
    - Para menciones: crea notificaciones directas a los usuarios mencionados.
    - NO crea notificaciones para comentarios sin menciones.

    Todos los endpoints requieren autenticación JWT.
    """

    @inject
    def __init__(self, solicitud_comentario_orchestrator: SolicitudComentarioOrchestrator):
        self.orchestrator = solicitud_comentario_orchestrator

    @route.post(
        "/{solicitud_id}/conversaciones/{conversacion_id}/comentarios",
        response={200: ApiResponse[MensajeOut]},
    )
    async def crear_comentario(
        self,
        request,
        solicitud_id: UUID,
        conversacion_id: UUID,
        data: Form[DataForm],
        files: File[list[UploadedFile]] = [],
    ):
        """
        Publica un nuevo comentario en una conversación vinculada a una solicitud.

        El usuario autenticado es el autor.
        La conversación debe estar abierta.
        La conversación debe pertenecer a la solicitud (bridge validation).

        Patrón dual payload (FormData + archivos) — estándar del proyecto:
        - data: JSON string con los campos del mensaje (serializado como DataForm)
        - files: lista de archivos con nombre con formato "token___nombre_real.ext"

        Comportamiento de notificaciones:
        - Comentario SIN menciones: NO crea ninguna notificación.
        - Comentario CON menciones: crea Notificacion para cada usuario mencionado,
          con NotificacionUsuario y NotificacionSolicitud (con conversacion y mensaje).
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
            msg = await self.orchestrator.crear_comentario(
                data=msg_data,
                solicitud_id=solicitud_id,
            )
        except BridgeValidationError as e:
            from ninja.errors import HttpError
            raise HttpError(
                409,
                f"La conversación '{conversacion_id}' no pertenece a la solicitud {solicitud_id}",
            )
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
