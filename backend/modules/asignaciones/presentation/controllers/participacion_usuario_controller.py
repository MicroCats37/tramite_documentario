"""
ParticipacionUsuarioController — controlador HTTP ligero para operaciones de participaciones de usuario.

Solo delega a ParticipacionUsuarioOrchestrator y retorna vía presenter.
Patrón 3: JSON Estricto — sin archivos.
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
from uuid import UUID

from asgiref.sync import sync_to_async

from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated
from injector import inject

from core.responses import ApiResponse, success_response
from modules.asignaciones.domain.services.orchestrators.participacion_usuario_orchestrator import (
    ParticipacionUsuarioOrchestrator,
)
from modules.asignaciones.presentation.schemas.periodo_in import (
    RetirarParticipacionIn,
)
from modules.tramites.presentation.presenters.solicitud_presenter import (
    SolicitudPresenter,
)


@api_controller("/participaciones-usuario", tags=["Participaciones de Usuario"], permissions=[IsAuthenticated])
class ParticipacionUsuarioController:
    """
    Controlador para gestión de participaciones de usuarios en períodos.

    Endpoints:
    1. POST /{participacion_id}/retirar — retira a un usuario de una participación activa
    """

    @inject
    def __init__(self, participacion_orchestrator: ParticipacionUsuarioOrchestrator):
        self.participacion_orchestrator = participacion_orchestrator

    @route.post("/{participacion_id}/retirar", response={200: ApiResponse[dict]})
    async def retirar_participacion(
        self,
        request,
        participacion_id: UUID,
        payload: RetirarParticipacionIn | None = None,
    ):
        """
        Retira a un usuario de una participación activa en un período.

        El usuario autenticado retira la participación identificada por {participacion_id}.

        El flujo:
        1. Valida que la participación existe (404 si no).
        2. Valida que la participación está activa (409 si ya finalizada).
        3. Valida que el período asociado no está CERRADO (409).
        4. Establece fecha_fin, retirado_por y motivo_retiro.
        5. Retorna la solicitud actualizada con todas sus asignaciones.
        """
        motivo = payload.motivo if payload else None

        solicitud = await self.participacion_orchestrator.retirar_participacion(
            participacion_id=participacion_id,
            usuario_id=request.auth.id,
            motivo=motivo,
        )

        presenter_sync = sync_to_async(
            SolicitudPresenter.present,
            thread_sensitive=True,
        )
        solicitud_out = await presenter_sync(solicitud)
        return success_response(solicitud_out.model_dump())
