"""
ConversacionFlujo — async flow for conversacion operations.

Handles:
- Creating a conversacion (optionally linked to a Solicitud via bridge).
- Posting a message to a conversacion (with attachments and mentions).
- Closing a conversacion.
- Notification hooks for mentions and area notifications.

All write operations are wrapped in @transaction.atomic().
"""

import logging
from datetime import datetime
from uuid import UUID

from asgiref.sync import sync_to_async
from django.db import transaction
from injector import inject

from modules.conversaciones.domain.constants import EstadoConversacion
from modules.conversaciones.domain.exceptions import (
    ConversacionCerradaError,
    ConversacionNotFoundError,
    MensajeNotFoundError,
)
from modules.conversaciones.domain.models import (
    Conversacion,
    Mensaje,
    SolicitudConversacion,
)
from modules.conversaciones.domain.schemas.conversacion_schemas import (
    ConversacionCreateData,
)
from modules.conversaciones.domain.schemas.mensaje_schemas import MensajeCreateData
from modules.conversaciones.domain.services.core.mensajeria_service import (
    MensajeriaCoreService,
)

logger = logging.getLogger(__name__)


class ConversacionFlujo:
    """
    Async flow for conversacion messaging operations.

    Each public method follows the pattern:
    async def _proceso_*(...) → wraps sync_to_async(self._*_atomica)

    @transaction.atomic() is applied to the sync inner methods only.
    """

    @inject
    def __init__(self, mensajeria_service: MensajeriaCoreService):
        self.mensajeria_service = mensajeria_service

    # ── Crear conversación ─────────────────────────────────────────────────────

    async def _proceso_crear_conversacion(
        self,
        data: ConversacionCreateData,
        solicitud_id: UUID | None = None,
    ) -> Conversacion:
        """
        Create a new conversacion, optionally linked to a Solicitud.

        If solicitud_id is provided, also creates the SolicitudConversacion bridge.

        1. Create conversacion (atomic).
        2. If solicitud_id, create bridge (atomic).

        Args:
            data: Conversacion creation data.
            solicitud_id: Optional solicitud ID to link the conversation to.

        Returns:
            The newly created Conversacion.
        """
        return await sync_to_async(
            self._crear_conversacion_atomica, thread_sensitive=True
        )(data=data, solicitud_id=solicitud_id)

    @transaction.atomic()
    def _crear_conversacion_atomica(
        self,
        data: ConversacionCreateData,
        solicitud_id: UUID | None = None,
    ) -> Conversacion:
        """
        Sync atomic version of _proceso_crear_conversacion.
        """
        conversacion = self.mensajeria_service.crear_conversacion(data)

        if solicitud_id is not None:
            self.mensajeria_service.crear_puente_solicitud(
                solicitud_id=solicitud_id,
                conversacion=conversacion,
            )

        return conversacion

    # ── Crear mensaje ──────────────────────────────────────────────────────────

    async def _proceso_crear_mensaje(self, data: MensajeCreateData) -> Mensaje:
        """
        Create a new mensaje in a conversacion.

        Validates that the conversacion is not closed before posting.

        1. Validate conversacion is open.
        2. Create mensaje with attachments and mentions (atomic).

        Args:
            data: Mensaje creation data.

        Returns:
            The newly created Mensaje.

        Raises:
            ConversacionCerradaError: if the conversacion is closed.
        """
        return await sync_to_async(
            self._crear_mensaje_atomica, thread_sensitive=True
        )(data=data)

    @transaction.atomic()
    def _crear_mensaje_atomica(self, data: MensajeCreateData) -> Mensaje:
        """
        Sync atomic version of _proceso_crear_mensaje.

        Phase 4 notification hooks:
        - Menciones (direct user notifications): each mentioned user receives
          a direct notification via NotificacionService.crear_notificacion_usuario().
          The service may raise NotImplementedError if the method is not yet available;
          in that case the hook silently logs a warning.
        - Area notifications: if the conversacion is linked to a Solicitud with
          an associated area, all active users in that area receive an area notification
          (excluding the autor_usuario). This requires the SolicitudConversacion bridge
          to be populated.
        """
        # Validate conversacion exists and is open
        try:
            conversacion = self.mensajeria_service.obtener_conversacion(data.conversacion_id)
        except Exception:
            raise

        if conversacion.fecha_cierre is not None:
            raise ConversacionCerradaError(data.conversacion_id)

        # Create mensaje (attachments and mentions created inside)
        mensaje = self.mensajeria_service.crear_mensaje(data)

        # ── Phase 4: Notification hooks ─────────────────────────────────────
        self._hook_notificaciones(mensaje, data)

        return mensaje

    def _hook_notificaciones(self, mensaje: Mensaje, data: MensajeCreateData) -> None:
        """
        Fire notification hooks after mensaje creation.

        This method is decoupled from the core transaction — it performs
        read-only queries to gather context and sends notifications via the
        notification service. It does NOT open new transactions.

        Menciones (direct user notifications):
            Calls NotificacionService.crear_notificacion_usuario() for each
            mentioned user. This may raise NotImplementedError if the service
            method is not yet implemented; in that case the hook logs a warning
            and continues without failing the message creation.

        Area notifications:
            DISABLED for normal comments. Normal comments create no area
            notification. Area notifications for comments are handled exclusively
            by the contextual endpoint (SolicitudComentarioFlujo) which has proper
            SolicitudConversacion bridge context.

            NOTE: The legacy _notify_area_if_linked call is commented out because
            it fired area notifications for ALL messages (including normal comments),
            violating the design rule that "normal comments do not notify". The
            generic conversation endpoint no longer sends area notifications.
        """
        try:
            from modules.notificaciones.domain.services.core.notificacion_service import (
                NotificacionService,
            )
        except ImportError:
            # Notification module not available — skip silently
            return

        try:
            notif_service = NotificacionService()
        except Exception:
            # DI or configuration issue — skip silently
            return

        # ── Menciones: direct user notifications ───────────────────────────
        if data.menciones:
            self._notify_menciones(notif_service, mensaje, data)

        # ── Area notifications (DISABLED) ──────────────────────────────────
        # NORMAL COMMENTS: no area notification.
        # Area notifications for bridged conversations are handled by
        # SolicitudComentarioFlujo._dispatch_menciones (contextual endpoint).
        # _notify_area_if_linked created COMENTARIO_CREADO area notifications
        # for ALL messages, including normal human comments — which violates
        # the design rule that normal comments do not notify.
        # self._notify_area_if_linked(notif_service, mensaje, data)

    def _notify_menciones(
        self,
        notif_service: "NotificacionService",
        mensaje: Mensaje,
        data: MensajeCreateData,
    ) -> None:
        """
        Send direct notifications to each mentioned user.

        Graceful degradation: if notification creation fails for a specific user,
        log and continue with the remaining users.
        """
        from modules.notificaciones.domain.constants import (
            AmbitoNotificacion,
            EventoNotificacion,
            PrioridadNotificacion,
        )

        if not data.menciones:
            return

        for mencion in data.menciones:
            try:
                notif_service.crear_notificacion_usuario(
                    usuario_id=mencion.usuario_id,
                    titulo=f"Nuevo mensaje de @{mensaje.autor_usuario_id}",
                    mensaje=mensaje.contenido or "(mensaje sin texto)",
                    ambito=AmbitoNotificacion.SOLICITUD,
                    evento=EventoNotificacion.COMENTARIO_MENCION,
                    prioridad=PrioridadNotificacion.NORMAL,
                    generada_por_id=mensaje.autor_usuario_id,
                    ocurrido_en=datetime.now(),
                )
            except Exception as e:
                logger.warning(
                    "Failed to send mention notification to user %s: %s",
                    mencion.usuario_id,
                    e,
                )

    def _notify_area_if_linked(
        self,
        notif_service: "NotificacionService",
        mensaje: Mensaje,
        data: MensajeCreateData,
    ) -> None:
        """
        Send area notification if the conversacion is linked to a Solicitud with area.
        """
        from modules.notificaciones.domain.constants import (
            AmbitoNotificacion,
            EventoNotificacion,
            PrioridadNotificacion,
        )

        try:
            # Check if this conversacion is linked to a Solicitud with area
            bridge = SolicitudConversacion.objects.filter(
                conversacion_id=mensaje.conversacion_id
            ).select_related("solicitud__area").first()

            if bridge is None or not hasattr(bridge, "solicitud") or bridge.solicitud is None:
                return

            area = getattr(bridge.solicitud, "area", None)
            if area is None:
                return

            notif_service.crear_notificacion_area(
                area=area,
                titulo=f"Nuevo mensaje en conversación",
                mensaje=mensaje.contenido or "(mensaje sin texto)",
                ambito=AmbitoNotificacion.SOLICITUD,
                evento=EventoNotificacion.COMENTARIO_CREADO,
                prioridad=PrioridadNotificacion.NORMAL,
                generada_por_id=mensaje.autor_usuario_id,
                ocurrido_en=datetime.now(),
                solicitud=bridge.solicitud,
            )
        except Exception as e:
            # Non-critical: log and continue without failing message creation
            logger.warning("Failed to send area notification: %s", e)

    # ── Cerrar conversación ────────────────────────────────────────────────────

    async def _proceso_cerrar_conversacion(
        self,
        conversacion_id: UUID,
        cerrado_por_id: UUID,
    ) -> Conversacion:
        """
        Close a conversacion.

        1. Obtain conversacion with lock.
        2. Validate it is not already closed.
        3. Close it (atomic).

        Args:
            conversacion_id: UUID of the conversacion.
            cerrado_por_id: ID of the user closing the conversation.

        Returns:
            The updated Conversacion.
        """
        return await sync_to_async(
            self._cerrar_conversacion_atomica, thread_sensitive=True
        )(conversacion_id=conversacion_id, cerrado_por_id=cerrado_por_id)

    @transaction.atomic()
    def _cerrar_conversacion_atomica(
        self,
        conversacion_id: UUID,
        cerrado_por_id: UUID,
    ) -> Conversacion:
        """
        Sync atomic version of _proceso_cerrar_conversacion.
        """
        try:
            conversacion = (
                Conversacion.objects.select_for_update().get(id=conversacion_id)
            )
        except Conversacion.DoesNotExist:
            raise ConversacionNotFoundError(conversacion_id)

        if conversacion.fecha_cierre is not None:
            # Already closed — return as-is (idempotent)
            return conversacion

        return self.mensajeria_service.cerrar_conversacion(
            conversacion=conversacion,
            cerrado_por_id=cerrado_por_id,
        )

    # ── Eliminar mensaje (soft-delete) ───────────────────────────────────────

    async def _proceso_eliminar_mensaje(
        self,
        mensaje_id: UUID,
        eliminado_por_id: UUID,
    ) -> Mensaje:
        """
        Soft-delete a mensaje.

        1. Obtain mensaje with lock.
        2. Validate it is not already deleted.
        3. Soft-delete it (atomic).

        Args:
            mensaje_id: UUID of the mensaje.
            eliminado_por_id: ID of the user deleting the message.

        Returns:
            The updated Mensaje.
        """
        return await sync_to_async(
            self._eliminar_mensaje_atomica, thread_sensitive=True
        )(mensaje_id=mensaje_id, eliminado_por_id=eliminado_por_id)

    @transaction.atomic()
    def _eliminar_mensaje_atomica(
        self,
        mensaje_id: UUID,
        eliminado_por_id: UUID,
    ) -> Mensaje:
        """
        Sync atomic version of _proceso_eliminar_mensaje.
        """
        from modules.conversaciones.domain.schemas.mensaje_schemas import MensajeDeleteData

        try:
            mensaje = (
                Mensaje.objects.select_for_update().get(id=mensaje_id)
            )
        except Mensaje.DoesNotExist:
            raise MensajeNotFoundError(mensaje_id)

        if mensaje.eliminado_at is not None:
            # Already deleted — return as-is (idempotent)
            return mensaje

        return self.mensajeria_service.eliminar_mensaje(
            mensaje=mensaje,
            data=MensajeDeleteData(eliminado_por_id=eliminado_por_id),
        )
