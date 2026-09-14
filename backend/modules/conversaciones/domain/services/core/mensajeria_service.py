"""
MensajeriaCoreService — synchronous domain operations for messaging.

NO transaction.atomic() here — the flujo provides atomicity when needed.
All operations are sync and reusable across flows.
"""

from datetime import datetime
from django.utils import timezone
from uuid import UUID

from injector import inject

from modules.conversaciones.domain.constants import EstadoConversacion
from modules.conversaciones.domain.exceptions import (
    ConversacionCerradaError,
    ConversacionNotFoundError,
    MensajeNotFoundError,
    UsuarioNotFoundError,
)
from modules.conversaciones.domain.models import (
    Conversacion,
    Mensaje,
    MensajeArchivoAdjunto,
    MensajeMencion,
    SolicitudConversacion,
)
from modules.conversaciones.domain.schemas.conversacion_schemas import (
    ConversacionCreateData,
    ConversacionUpdateData,
)
from modules.conversaciones.domain.schemas.mensaje_schemas import (
    MensajeArchivoAdjuntoData,
    MensajeCreateData,
    MensajeDeleteData,
    MensajeMencionData,
)


class MensajeriaCoreService:
    """
    Synchronous service for core messaging operations.

    Operations are sync and do NOT open transaction.atomic() internally.
    The calling flujo provides atomicity when composing multiple writes.
    """

    # ── Conversacion operations ───────────────────────────────────────────────

    def crear_conversacion(self, data: ConversacionCreateData) -> Conversacion:
        """
        Create a new Conversacion.

        Sync — for use inside transaction.atomic.
        """
        return Conversacion.objects.create(
            titulo=data.titulo,
            creada_por_id=data.creada_por_id,
            fecha_inicio=data.fecha_inicio,
        )

    def obtener_conversacion(self, conversacion_id: UUID) -> Conversacion:
        """
        Get a Conversacion by ID.

        Raises:
            ConversacionNotFoundError: if not found.
        """
        try:
            return Conversacion.objects.get(id=conversacion_id)
        except Conversacion.DoesNotExist:
            raise ConversacionNotFoundError(conversacion_id)

    def cerrar_conversacion(
        self,
        conversacion: Conversacion,
        cerrado_por_id: int,
        ahora: datetime | None = None,
    ) -> Conversacion:
        """
        Close a Conversacion (soft close — sets fecha_cierre and cerrado_por).

        Sync — for use inside transaction.atomic.
        """
        ahora = ahora or timezone.now()
        conversacion.fecha_cierre = ahora
        conversacion.cerrado_por_id = cerrado_por_id
        conversacion.save(update_fields=["fecha_cierre", "cerrado_por_id", "updated_at"])
        return conversacion

    # ── Mensaje operations ─────────────────────────────────────────────────────

    # ── System message helper ─────────────────────────────────────────────────

    def crear_mensaje_sistema(
        self,
        conversacion_id: UUID,
        contenido: str,
        fecha_envio: datetime | None = None,
    ) -> Mensaje:
        """
        Create a SISTEMA message with no autor, no attachments, no mentions.

        This is a thin convenience wrapper over crear_mensaje for system events
        that require contextual audit messages (period operations, closure, etc.).

        Sync — for use inside transaction.atomic.
        """
        data = MensajeCreateData(
            conversacion_id=conversacion_id,
            autor_usuario_id=None,
            contenido=contenido,
            tipo="SISTEMA",
            fecha_envio=fecha_envio or _now(),
        )
        return self.crear_mensaje(data)

    # ── Core crear_mensaje ────────────────────────────────────────────────────

    def crear_mensaje(self, data: MensajeCreateData) -> Mensaje:
        """
        Create a Mensaje along with its attachments and mentions.

        Does NOT send notifications — caller (flujo) handles that.

        Sync — for use inside transaction.atomic.

        Note: System messages (tipo=SISTEMA) have autor_usuario_id=None and
        do NOT support attachments or mentions.
        """
        mensaje = Mensaje.objects.create(
            conversacion_id=data.conversacion_id,
            autor_usuario_id=data.autor_usuario_id,
            contenido=data.contenido,
            tipo=data.tipo,
            fecha_envio=data.fecha_envio,
            mensaje_padre_id=data.mensaje_padre_id,
        )

        # System messages (autor=None) do not support attachments or mentions
        if data.autor_usuario_id is not None:
            # Create attachments
            for adjunto_data in data.archivos_adjuntos:
                self._crear_archivo_adjunto(mensaje, adjunto_data)

            # Create mentions
            for mencion_data in data.menciones:
                self._crear_mencion(mensaje, mencion_data)

        return mensaje

    def _crear_archivo_adjunto(
        self,
        mensaje: Mensaje,
        data: MensajeArchivoAdjuntoData,
    ) -> MensajeArchivoAdjunto:
        """Create a single MensajeArchivoAdjunto linked to a mensaje."""
        return MensajeArchivoAdjunto.objects.create(
            mensaje=mensaje,
            archivo=data.archivo,
            nombre_original=data.nombre_original,
            mime_type=data.mime_type,
            tamano_bytes=data.tamano_bytes,
            subido_por_id=data.subido_por_id,
            fecha_archivo=data.fecha_archivo,
            descripcion=data.descripcion,
        )

    def _crear_mencion(
        self,
        mensaje: Mensaje,
        data: MensajeMencionData,
    ) -> MensajeMencion:
        """Create a single MensajeMencion linked to a mensaje."""
        return MensajeMencion.objects.create(
            mensaje=mensaje,
            usuario_id=data.usuario_id,
        )

    def obtener_mensaje(self, mensaje_id: UUID) -> Mensaje:
        """
        Get a Mensaje by ID.

        Raises:
            MensajeNotFoundError: if not found.
        """
        try:
            return Mensaje.objects.get(id=mensaje_id)
        except Mensaje.DoesNotExist:
            raise MensajeNotFoundError(mensaje_id)

    def eliminar_mensaje(
        self,
        mensaje: Mensaje,
        data: MensajeDeleteData,
        ahora: datetime | None = None,
    ) -> Mensaje:
        """
        Soft-delete a Mensaje (sets eliminado_at and eliminado_por).

        Sync — for use inside transaction.atomic.
        """
        ahora = ahora or timezone.now()
        mensaje.eliminado_at = ahora
        mensaje.eliminado_por_id = data.eliminado_por_id
        mensaje.save(update_fields=["eliminado_at", "eliminado_por_id", "updated_at"])
        return mensaje

    # ── SolicitudConversacion operations ──────────────────────────────────────

    def crear_puente_solicitud(
        self,
        solicitud_id: UUID,
        conversacion: Conversacion,
    ) -> SolicitudConversacion:
        """
        Create the SolicitudConversacion bridge.

        Sync — for use inside transaction.atomic.
        """
        return SolicitudConversacion.objects.create(
            solicitud_id=solicitud_id,
            conversacion=conversacion,
        )

    # ── Bulk fetch helpers ─────────────────────────────────────────────────────

    def listar_mensajes_con_adjuntos(
        self,
        conversacion_id: UUID,
    ) -> list[Mensaje]:
        """
        List all non-eliminated mensajes for a conversacion, with attachments prefetched.

        Sync — for use inside transaction.atomic or as standalone query.
        """
        return list(
            Mensaje.objects.filter(
                conversacion_id=conversacion_id,
                eliminado_at__isnull=True,
            )
            .select_related("autor_usuario")
            .prefetch_related("archivos_adjuntos", "menciones")
            .order_by("fecha_envio")
        )

    def obtener_conversacion_con_mensajes(
        self,
        conversacion_id: UUID,
    ) -> Conversacion:
        """
        Get a Conversacion with all its non-eliminated mensajes loaded.

        Raises:
            ConversacionNotFoundError: if not found.
        """
        try:
            return (
                Conversacion.objects.prefetch_related(
                    Mensaje.objects.filter(eliminado_at__isnull=True)
                    .select_related("autor_usuario")
                    .prefetch_related("archivos_adjuntos", "menciones")
                    .order_by("fecha_envio")
                )
                .get(id=conversacion_id)
            )
        except Conversacion.DoesNotExist:
            raise ConversacionNotFoundError(conversacion_id)
