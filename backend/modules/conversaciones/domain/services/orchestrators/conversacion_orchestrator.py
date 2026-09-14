"""
ConversacionOrchestrator — thin async facade for conversacion HTTP endpoints.

One public method per controller endpoint.
Only delegates to the flujo — no business logic here.
"""

from uuid import UUID

from injector import inject

from modules.conversaciones.domain.models import Conversacion, Mensaje
from modules.conversaciones.domain.schemas.conversacion_schemas import (
    ConversacionCreateData,
)
from modules.conversaciones.domain.schemas.mensaje_schemas import MensajeCreateData
from modules.conversaciones.domain.services.flujos.conversacion_flujo import (
    ConversacionFlujo,
)


class ConversacionOrchestrator:
    """
    Thin async facade for conversacion operations.

    All methods are async and delegate to the flujo.
    No business logic — pure delegation.
    """

    @inject
    def __init__(self, conversacion_flujo: ConversacionFlujo):
        self.conversacion_flujo = conversacion_flujo

    # ── Conversacion ──────────────────────────────────────────────────────────

    async def crear_conversacion(
        self,
        data: ConversacionCreateData,
        solicitud_id: UUID | None = None,
    ) -> Conversacion:
        """
        Create a new conversacion, optionally linked to a Solicitud.

        Args:
            data: Conversacion creation data.
            solicitud_id: Optional solicitud ID to link.

        Returns:
            Newly created Conversacion.
        """
        return await self.conversacion_flujo._proceso_crear_conversacion(
            data=data,
            solicitud_id=solicitud_id,
        )

    async def cerrar_conversacion(
        self,
        conversacion_id: UUID,
        cerrado_por_id: UUID,
    ) -> Conversacion:
        """
        Close a conversacion.

        Args:
            conversacion_id: UUID of the conversacion.
            cerrado_por_id: ID of the user closing.

        Returns:
            Updated Conversacion.
        """
        return await self.conversacion_flujo._proceso_cerrar_conversacion(
            conversacion_id=conversacion_id,
            cerrado_por_id=cerrado_por_id,
        )

    # ── Mensaje ──────────────────────────────────────────────────────────────

    async def crear_mensaje(self, data: MensajeCreateData) -> Mensaje:
        """
        Post a new mensaje to a conversacion.

        Args:
            data: Mensaje creation data.

        Returns:
            Newly created Mensaje.
        """
        return await self.conversacion_flujo._proceso_crear_mensaje(data=data)

    async def eliminar_mensaje(
        self,
        mensaje_id: UUID,
        eliminado_por_id: UUID,
    ) -> Mensaje:
        """
        Soft-delete a mensaje.

        Args:
            mensaje_id: UUID of the mensaje.
            eliminado_por_id: ID of the user deleting.

        Returns:
            Updated Mensaje.
        """
        return await self.conversacion_flujo._proceso_eliminar_mensaje(
            mensaje_id=mensaje_id,
            eliminado_por_id=eliminado_por_id,
        )
