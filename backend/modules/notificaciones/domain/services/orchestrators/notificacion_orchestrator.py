"""
NotificacionOrchestrator — fachada asíncrona ligera para controladores de Notificación.

Delegación de operaciones a NotificacionFlujo.
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
from uuid import UUID

from injector import inject

from modules.notificaciones.domain.services.flujos.notificacion_flujo import (
    NotificacionFlujo,
)


class NotificacionOrchestrator:
    """
    Fachada asíncrona ligera — delega operaciones de notificación a NotificacionFlujo.
    """

    @inject
    def __init__(self, notificacion_flujo: NotificacionFlujo):
        self.notificacion_flujo = notificacion_flujo

    async def marcar_vista(
        self,
        notificacion_id: UUID,
        usuario_id: int,
    ):
        """
        Marca una notificación como vista para el usuario autenticado.

        Es idempotente: si ya fue marcada, no cambia el timestamp existente.

        Args:
            notificacion_id: UUID de la Notificacion.
            usuario_id: ID del usuario que marca como vista.

        Returns:
            Instancia de Notificacion con relaciones precargadas.

        Raises:
            HttpError: 404 si la notificación no existe.
        """
        return await self.notificacion_flujo._proceso_marcar_vista(
            notificacion_id=notificacion_id,
            usuario_id=usuario_id,
        )

    async def abrir(
        self,
        notificacion_id: UUID,
        usuario_id: int,
    ):
        """
        Marca una notificación como abierta para el usuario autenticado.

        Es idempotente: si ya fue abierta, no cambia el timestamp existente.

        Invariant: no puede haber abierta_at sin vista_at. Si vista_at es NULL,
        se setea automáticamente junto con abierta_at.

        Args:
            notificacion_id: UUID de la Notificacion.
            usuario_id: ID del usuario que marca como abierta.

        Returns:
            Instancia de Notificacion con relaciones precargadas.

        Raises:
            HttpError: 404 si la notificación no existe.
        """
        return await self.notificacion_flujo._proceso_abrir(
            notificacion_id=notificacion_id,
            usuario_id=usuario_id,
        )

    async def descartar(
        self,
        notificacion_id: UUID,
        usuario_id: int,
    ):
        """
        Descarta una notificación para el usuario autenticado.

        Es idempotente: si ya fue descartada, no cambia el timestamp existente.

        Args:
            notificacion_id: UUID de la Notificacion.
            usuario_id: ID del usuario que descarta.

        Returns:
            Instancia de Notificacion con relaciones precargadas.

        Raises:
            HttpError: 404 si la notificación no existe.
        """
        return await self.notificacion_flujo._proceso_descartar(
            notificacion_id=notificacion_id,
            usuario_id=usuario_id,
        )
