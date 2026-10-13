"""
SolicitudComentarioFlujo — async flow for contextual solicitud comment operations.

Handles:
- Creating a comment on a conversation linked to a solicitud.
- Validating the SolicitudConversacion bridge.
- Dispatching mention notifications with proper NotificacionSolicitud context.
- Creating system messages (timeline entries) with no notifications.

Patrón: async flujo → transaction.atomic en método sync interno.
"""

import logging
from datetime import datetime
from uuid import UUID

from asgiref.sync import sync_to_async
from django.db import transaction
from injector import inject

from modules.conversaciones.domain.constants import TipoMensaje
from modules.conversaciones.domain.exceptions import BridgeValidationError
from modules.conversaciones.domain.models import (
    Mensaje,
    SolicitudConversacion,
)
from modules.conversaciones.domain.schemas.mensaje_schemas import MensajeCreateData
from modules.conversaciones.domain.services.core.mensajeria_service import (
    MensajeriaCoreService,
)
from modules.notificaciones.domain.constants import (
    AmbitoNotificacion,
    EventoNotificacion,
    PrioridadNotificacion,
)
from modules.notificaciones.domain.registry import get_event_config
from modules.notificaciones.domain.services.core.notificacion_service import (
    NotificacionService,
)

logger = logging.getLogger(__name__)


class SolicitudComentarioFlujo:
    """
    Async flow for contextual comentario operations on solicitud-linked conversations.

    This flujo is used by the new contextual endpoint:
    POST /solicitudes/{solicitud_id}/conversaciones/{conversacion_id}/comentarios

    Key behaviors:
    - Validates that the conversacion belongs to the solicitud (bridge check).
    - Creates Mensaje with attachments — NO notification for normal comments.
    - For mentions: creates Mensaje + MensajeMencion + Notificacion +
      NotificacionUsuario + NotificacionSolicitud (with conversacion/mensaje).
    - System messages: creates Mensaje with tipo=SISTEMA and autor_usuario=None,
      with NO notifications.
    """

    @inject
    def __init__(
        self,
        mensajeria_service: MensajeriaCoreService,
        notificacion_service: NotificacionService,
    ):
        self.mensajeria_service = mensajeria_service
        self.notificacion_service = notificacion_service

    async def _proceso_crear_comentario(
        self,
        data: MensajeCreateData,
        solicitud_id: UUID,
    ) -> Mensaje:
        """
        Create a contextual comment on a solicitud-linked conversation.

        1. Validate bridge: conversacion must belong to solicitud.
        2. Validate conversacion is open.
        3. Create mensaje with attachments and mentions (atomic).
        4. Dispatch mention notifications if any.

        Args:
            data: Mensaje creation data.
            solicitud_id: The solicitud ID to validate against.

        Returns:
            The newly created Mensaje.

        Raises:
            BridgeValidationError: if the conversacion does not belong to the solicitud.
            ConversacionCerradaError: if the conversacion is closed.
        """
        return await sync_to_async(
            self._crear_comentario_atomica, thread_sensitive=True
        )(data=data, solicitud_id=solicitud_id)

    async def _proceso_crear_mensaje_sistema(
        self,
        conversacion_id: UUID,
        contenido: str,
        solicitud_id: UUID,
    ) -> Mensaje:
        """
        Create a system message (timeline entry) in a solicitud-linked conversation.

        System messages have tipo=SISTEMA and autor_usuario=None.
        They do NOT create any notifications.

        1. Validate bridge: conversacion must belong to solicitud.
        2. Validate conversacion is open.
        3. Create system mensaje (atomic) — no notifications.

        Args:
            conversacion_id: UUID of the conversacion.
            contenido: Text content of the system message.
            solicitud_id: The solicitud ID to validate against.

        Returns:
            The newly created Mensaje.

        Raises:
            BridgeValidationError: if the conversacion does not belong to the solicitud.
            ConversacionCerradaError: if the conversacion is closed.
        """
        return await sync_to_async(
            self._crear_mensaje_sistema_atomica, thread_sensitive=True
        )(conversacion_id=conversacion_id, contenido=contenido, solicitud_id=solicitud_id)

    @transaction.atomic()
    def _crear_mensaje_sistema_atomica(
        self,
        conversacion_id: UUID,
        contenido: str,
        solicitud_id: UUID,
    ) -> Mensaje:
        """
        Sync atomic version of _proceso_crear_mensaje_sistema.

        Raises:
            BridgeValidationError: if the conversacion does not belong to the solicitud.
            ConversacionCerradaError: if the conversacion is closed.
        """
        # 1. Validate bridge
        try:
            bridge = SolicitudConversacion.objects.select_related(
                "solicitud"
            ).get(conversacion_id=conversacion_id)
        except SolicitudConversacion.DoesNotExist:
            bridge = None

        if bridge is None:
            raise BridgeValidationError(
                solicitud_id=solicitud_id,
                conversacion_id=conversacion_id,
            )

        if bridge.solicitud_id != solicitud_id:
            raise BridgeValidationError(
                solicitud_id=solicitud_id,
                conversacion_id=conversacion_id,
            )

        # 2. Validate conversacion is open
        conversacion = self.mensajeria_service.obtener_conversacion(conversacion_id)
        if conversacion.fecha_cierre is not None:
            from modules.conversaciones.domain.exceptions import (
                ConversacionCerradaError,
            )
            raise ConversacionCerradaError(conversacion_id)

        # 3. Create system mensaje — no autor, no notifications
        data = MensajeCreateData(
            conversacion_id=conversacion_id,
            autor_usuario_id=None,
            contenido=contenido,
            tipo=TipoMensaje.SISTEMA,
            fecha_envio=datetime.now(),
        )
        return self.mensajeria_service.crear_mensaje(data)

    @transaction.atomic()
    def _crear_comentario_atomica(
        self,
        data: MensajeCreateData,
        solicitud_id: UUID,
    ) -> Mensaje:
        """
        Sync atomic version of _proceso_crear_comentario.

        Raises:
            BridgeValidationError: if the conversacion does not belong to the solicitud.
            ConversacionCerradaError: if the conversacion is closed.
        """
        # 1. Validate bridge
        try:
            bridge = SolicitudConversacion.objects.select_related(
                "solicitud"
            ).get(conversacion_id=data.conversacion_id)
        except SolicitudConversacion.DoesNotExist:
            bridge = None

        if bridge is None:
            # Bridge not found — conversacion is not linked to any solicitud
            raise BridgeValidationError(
                solicitud_id=solicitud_id,
                conversacion_id=data.conversacion_id,
            )

        if bridge.solicitud_id != solicitud_id:
            # Bridge exists but points to a different solicitud
            raise BridgeValidationError(
                solicitud_id=solicitud_id,
                conversacion_id=data.conversacion_id,
            )

        # 2. Validate conversacion is open
        conversacion = self.mensajeria_service.obtener_conversacion(
            data.conversacion_id
        )
        if conversacion.fecha_cierre is not None:
            from modules.conversaciones.domain.exceptions import (
                ConversacionCerradaError,
            )
            raise ConversacionCerradaError(data.conversacion_id)

        # 3. Create mensaje (attachments and mentions created inside)
        mensaje = self.mensajeria_service.crear_mensaje(data)

        # 4. Dispatch mention notifications if any (outside atomic — read-only queries)
        if data.menciones:
            self._dispatch_menciones(mensaje, data, bridge.solicitud)

        return mensaje

    def _dispatch_menciones(
        self,
        mensaje: Mensaje,
        data: MensajeCreateData,
        solicitud,  # Solicitud instance
    ) -> None:
        """
        Send mention notifications for each mentioned user.

        Creates:
        - Notificacion (event: COMENTARIO_MENCION)
        - NotificacionUsuario for each mentioned user
        - NotificacionSolicitud with conversacion and mensaje context

        Note: Does NOT create area notifications (per design — normal comment
        creates no notification; mentions create only user-direct notifications).

        Raises:
            NotificacionEventoNoRegistradoError: if the event is not registered
                in the notification registry.
            Exception: re-raises any unexpected exception from notification creation
                after logging, so comment+notification consistency is preserved.
        """
        from modules.notificaciones.domain.exceptions import (
            NotificacionEventoNoRegistradoError,
        )

        # Get priority from registry
        config = get_event_config(
            AmbitoNotificacion.SOLICITUD,
            EventoNotificacion.COMENTARIO_MENCION,
        )
        prioridad = (
            config.prioridad_default
            if config and config.prioridad_default
            else PrioridadNotificacion.NORMAL
        )

        for mencion in data.menciones:
            try:
                self.notificacion_service.crear_notificacion_usuario(
                    usuario_id=mencion.usuario_id,
                    titulo="Te mencionaron en un comentario",
                    mensaje=mensaje.contenido or "(mensaje sin texto)",
                    ambito=AmbitoNotificacion.SOLICITUD,
                    evento=EventoNotificacion.COMENTARIO_MENCION,
                    prioridad=prioridad,
                    generada_por_id=mensaje.autor_usuario_id,
                    ocurrido_en=datetime.now(),
                    solicitud=solicitud,
                    conversacion_id=str(mensaje.conversacion_id),
                    mensaje_id=str(mensaje.id),
                )
            except NotificacionEventoNoRegistradoError:
                # Domain exception — re-raise so the whole operation fails
                logger.error(
                    "Mention notification event not registered for user %s: "
                    "ambito=SOLICITUD, evento=COMENTARIO_MENCION",
                    mencion.usuario_id,
                )
                raise
            except Exception as e:
                # Unexpected error — re-raise after logging to preserve
                # comment+notification consistency for mentions
                logger.error(
                    "Failed to send mention notification to user %s: %s",
                    mencion.usuario_id,
                    e,
                )
                raise
