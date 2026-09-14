"""
SolicitudComentarioOrchestrator — thin async facade for contextual solicitud comment endpoint.

One public method per controller endpoint.
Only delegates to the flujo — no business logic here.
"""

from uuid import UUID

from injector import inject

from modules.conversaciones.domain.models import Mensaje
from modules.conversaciones.domain.schemas.mensaje_schemas import MensajeCreateData
from modules.conversaciones.domain.services.flujos.solicitud_comentario_flujo import (
    SolicitudComentarioFlujo,
)


class SolicitudComentarioOrchestrator:
    """
    Thin async facade for contextual comentario operations on solicitud conversations.

    All methods are async and delegate to the flujo.
    No business logic — pure delegation.
    """

    @inject
    def __init__(self, solicitud_comentario_flujo: SolicitudComentarioFlujo):
        self.solicitud_comentario_flujo = solicitud_comentario_flujo

    async def crear_comentario(
        self,
        data: MensajeCreateData,
        solicitud_id: UUID,
    ) -> Mensaje:
        """
        Create a contextual comment on a solicitud-linked conversation.

        Args:
            data: Mensaje creation data.
            solicitud_id: The solicitud ID to validate against.

        Returns:
            Newly created Mensaje.
        """
        return await self.solicitud_comentario_flujo._proceso_crear_comentario(
            data=data,
            solicitud_id=solicitud_id,
        )
