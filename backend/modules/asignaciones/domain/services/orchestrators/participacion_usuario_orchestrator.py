"""
ParticipacionUsuarioOrchestrator — fachada asíncrona ligera para controladores de Participación de Usuario.

Delegación de operaciones a ParticipacionUsuarioFlujo.
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
from uuid import UUID

from injector import inject

from modules.asignaciones.domain.services.flujos.participacion_usuario_flujo import (
    ParticipacionUsuarioFlujo,
)


class ParticipacionUsuarioOrchestrator:
    """
    Fachada asíncrona ligera — delega operaciones de participación de usuario a ParticipacionUsuarioFlujo.
    """

    @inject
    def __init__(self, participacion_usuario_flujo: ParticipacionUsuarioFlujo):
        self.participacion_usuario_flujo = participacion_usuario_flujo

    async def retirar_participacion(
        self,
        participacion_id: UUID,
        usuario_id: UUID,
        motivo: str | None = None,
    ):
        """
        Retira a un usuario de una participación activa en un período.

        Args:
            participacion_id: UUID del SolicitudAsignacionUsuario.
            usuario_id: UUID del usuario que retira la participación.
            motivo: Motivo opcional del retiro.

        Returns:
            Instancia de Solicitud (padre de la participación).
        """
        return await self.participacion_usuario_flujo._proceso_retirar(
            participacion_id=participacion_id,
            usuario_id=usuario_id,
            motivo=motivo,
        )
