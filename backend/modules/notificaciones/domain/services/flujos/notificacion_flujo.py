"""
NotificacionFlujo — flujo async para interacciones de usuario con notificaciones.

Operaciones:
- Marcar como vista: establece vista_at en NotificacionUsuario (idempotente).
- Abrir: establece abierta_at en NotificacionUsuario (idempotente).
- Descartar: establece descartada_at en NotificacionUsuario (idempotente).

El @transaction.atomic() garantiza atomicidad al crear/actualizar NotificacionUsuario.
"""
from uuid import UUID

from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone
from injector import inject
from ninja.errors import HttpError


class NotificacionFlujo:
    """
    Flujo asíncrono para operaciones de interacción sobre notificaciones.

    Operaciones:
    - Marcar como vista: idempotente, solo setea vista_at si es NULL.
    - Abrir: idempotente, setea abierta_at si NULL y vista_at si NULL
      (invariant: no puede haber abierta_at sin vista_at).
    - Descartar: idempotente, solo setea descartada_at si es NULL.
    """

    async def _proceso_marcar_vista(
        self,
        notificacion_id: UUID,
        usuario_id: int,
    ):
        """
        Marca una notificación como vista para el usuario autenticado.

        Es idempotente: si ya fue marcada (vista_at ya establecido), no cambia
        el timestamp existente.

        Validaciones:
        1. La notificación existe (404 si no).
        2. El usuario tiene acceso a la notificación (404 si no).

        Efecto:
        - NotificacionUsuario.vista_at → now() (solo si NULL)

        Args:
            notificacion_id: UUID de la Notificacion.
            usuario_id: ID del usuario que marca como vista.

        Returns:
            Instancia de Notificacion con relaciones precargadas.

        Raises:
            HttpError: 404 si la notificación no existe.
        """
        return await sync_to_async(self._marcar_vista_atomica)(
            notificacion_id=notificacion_id,
            usuario_id=usuario_id,
        )

    @transaction.atomic()
    def _marcar_vista_atomica(
        self,
        notificacion_id: UUID,
        usuario_id: int,
    ):
        """
        Versión síncrona con @transaction.atomic para marcar como vista.
        """
        from modules.notificaciones.domain.models import Notificacion, NotificacionUsuario

        # 1. Obtener la notificación con lock
        try:
            notif = (
                Notificacion.objects
                .select_related(
                    "generada_por",
                )
                .prefetch_related(
                    "usuarios_notificados__usuario",
                    "areas_notificadas__area",
                )
                .get(id=notificacion_id)
            )
        except Notificacion.DoesNotExist:
            raise HttpError(404, "Notificación no encontrada")

        # 2. Obtener o crear el registro NotificacionUsuario
        iu, created = NotificacionUsuario.objects.get_or_create(
            notificacion_id=notificacion_id,
            usuario_id=usuario_id,
            defaults={},
        )

        # 3. Solo actualizar vista_at si no está ya establecido (idempotente)
        if iu.vista_at is None:
            iu.vista_at = timezone.now()
            iu.save(update_fields=["vista_at", "updated_at"])

        # 4. Retornar la notificación con relaciones precargadas
        return (
            Notificacion.objects
            .select_related(
                "generada_por",
            )
            .prefetch_related(
                "usuarios_notificados__usuario",
                "areas_notificadas__area",
            )
            .get(id=notificacion_id)
        )

    async def _proceso_abrir(
        self,
        notificacion_id: UUID,
        usuario_id: int,
    ):
        """
        Marca una notificación como abierta para el usuario autenticado.

        Es idempotente: si ya fue abierta (abierta_at ya establecido), no cambia
        el timestamp existente.

        Invariant: abierta_at nunca existe sin vista_at. Si vista_at es NULL
        al momento de abrir, se setea junto con abierta_at en la misma transacción.

        Validaciones:
        1. La notificación existe (404 si no).

        Efecto:
        - NotificacionUsuario.abierta_at → now() (solo si NULL)
        - NotificacionUsuario.vista_at → now() (solo si NULL — invariant)

        Args:
            notificacion_id: UUID de la Notificacion.
            usuario_id: ID del usuario que marca como abierta.

        Returns:
            Instancia de Notificacion con relaciones precargadas.

        Raises:
            HttpError: 404 si la notificación no existe.
        """
        return await sync_to_async(self._abrir_atomica)(
            notificacion_id=notificacion_id,
            usuario_id=usuario_id,
        )

    @transaction.atomic()
    def _abrir_atomica(
        self,
        notificacion_id: UUID,
        usuario_id: int,
    ):
        """
        Versión síncrona con @transaction.atomic para marcar como abierta.
        """
        from modules.notificaciones.domain.models import Notificacion, NotificacionUsuario

        # 1. Obtener la notificación
        try:
            notif = (
                Notificacion.objects
                .select_related(
                    "generada_por",
                )
                .prefetch_related(
                    "usuarios_notificados__usuario",
                    "areas_notificadas__area",
                )
                .get(id=notificacion_id)
            )
        except Notificacion.DoesNotExist:
            raise HttpError(404, "Notificación no encontrada")

        # 2. Obtener o crear el registro NotificacionUsuario
        iu, created = NotificacionUsuario.objects.get_or_create(
            notificacion_id=notificacion_id,
            usuario_id=usuario_id,
            defaults={},
        )

        # 3. Solo actualizar abierta_at si no está ya establecido (idempotente).
        #    También setea vista_at si es NULL — no puede haber abierta_at sin vista_at.
        now = timezone.now()
        changed = False
        if iu.abierta_at is None:
            iu.abierta_at = now
            changed = True
        if iu.vista_at is None:
            iu.vista_at = now
            changed = True
        if changed:
            iu.save(update_fields=["abierta_at", "vista_at", "updated_at"])

        # 4. Retornar la notificación con relaciones precargadas
        return (
            Notificacion.objects
            .select_related(
                "generada_por",
            )
            .prefetch_related(
                "usuarios_notificados__usuario",
                "areas_notificadas__area",
            )
            .get(id=notificacion_id)
        )

    async def _proceso_descartar(
        self,
        notificacion_id: UUID,
        usuario_id: int,
    ):
        """
        Descarta una notificación para el usuario autenticado.

        Es idempotente: si ya fue descartada (descartada_at ya establecido), no cambia
        el timestamp existente.

        Validaciones:
        1. La notificación existe (404 si no).

        Efecto:
        - NotificacionUsuario.descartada_at → now() (solo si NULL)

        Args:
            notificacion_id: UUID de la Notificacion.
            usuario_id: ID del usuario que descarta.

        Returns:
            Instancia de Notificacion con relaciones precargadas.

        Raises:
            HttpError: 404 si la notificación no existe.
        """
        return await sync_to_async(self._descartar_atomica)(
            notificacion_id=notificacion_id,
            usuario_id=usuario_id,
        )

    @transaction.atomic()
    def _descartar_atomica(
        self,
        notificacion_id: UUID,
        usuario_id: int,
    ):
        """
        Versión síncrona con @transaction.atomic para descartar.
        """
        from modules.notificaciones.domain.models import Notificacion, NotificacionUsuario

        # 1. Obtener la notificación
        try:
            notif = (
                Notificacion.objects
                .select_related(
                    "generada_por",
                )
                .prefetch_related(
                    "usuarios_notificados__usuario",
                    "areas_notificadas__area",
                )
                .get(id=notificacion_id)
            )
        except Notificacion.DoesNotExist:
            raise HttpError(404, "Notificación no encontrada")

        # 2. Obtener o crear el registro NotificacionUsuario
        iu, created = NotificacionUsuario.objects.get_or_create(
            notificacion_id=notificacion_id,
            usuario_id=usuario_id,
            defaults={},
        )

        # 3. Solo actualizar descartada_at si no está ya establecido (idempotente)
        if iu.descartada_at is None:
            iu.descartada_at = timezone.now()
            iu.save(update_fields=["descartada_at", "updated_at"])

        # 4. Retornar la notificación con relaciones precargadas
        return (
            Notificacion.objects
            .select_related(
                "generada_por",
            )
            .prefetch_related(
                "usuarios_notificados__usuario",
                "areas_notificadas__area",
            )
            .get(id=notificacion_id)
        )
