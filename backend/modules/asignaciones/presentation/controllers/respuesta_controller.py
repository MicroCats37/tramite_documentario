"""
RespuestaController — controlador HTTP ligero para operaciones sobre respuestas formales.

Solo delega a PeriodoOrchestrator y retorna vía presenter.
Patrón 3: JSON Estricto — sin archivos.
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
from uuid import UUID

from asgiref.sync import sync_to_async

from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated
from injector import inject

from core.responses import ApiResponse, success_response
from modules.asignaciones.domain.services.orchestrators.periodo_orchestrator import (
    PeriodoOrchestrator,
)
from modules.asignaciones.presentation.schemas.respuesta_out import RespuestaOut
from modules.asignaciones.presentation.presenters.respuesta_presenter import (
    RespuestaPresenter,
)


@api_controller("/respuestas", tags=["Respuestas"], permissions=[IsAuthenticated])
class RespuestaController:
    """
    Controlador para gestión de respuestas formales de áreas.

    Endpoints:
    1. POST /{respuesta_id}/emitir — emite una respuesta en estado BORRADOR
    2. POST /{respuesta_id}/anular — anula una respuesta en estado EMITIDA
    3. POST /{respuesta_id}/rectificar — rectifica una respuesta en estado EMITIDA
    """

    @inject
    def __init__(self, periodo_orchestrator: PeriodoOrchestrator):
        self.periodo_orchestrator = periodo_orchestrator

    @route.post("/{respuesta_id}/emitir", response={200: ApiResponse[RespuestaOut]})
    async def emitir_respuesta(
        self,
        request,
        respuesta_id: UUID,
    ):
        """
        Emite una respuesta que se encuentra en estado BORRADOR.

        La emisión es irreversible: transiciona la respuesta de BORRADOR a EMITIDA,
        registrando la fecha de emisión y el usuario que la emitió.

        El flujo:
        1. Valida que la respuesta existe (404 si no).
        2. Valida que la respuesta está en estado BORRADOR (400 si no).
        3. Valida que el período no está CERRADO (409 si cerrado).
        4. Transiciona la respuesta a EMITIDA (fecha_emision, emitido_por).
        5. Retorna la respuesta actualizada.
        """
        respuesta = await self.periodo_orchestrator.emitir_respuesta(
            respuesta_id=respuesta_id,
            usuario_id=request.auth.id,
        )

        presenter_sync = sync_to_async(
            RespuestaPresenter.present,
            thread_sensitive=True,
        )
        respuesta_out = await presenter_sync(respuesta)
        return success_response(respuesta_out.model_dump())

    @route.post("/{respuesta_id}/anular", response={200: ApiResponse[RespuestaOut]})
    async def anular_respuesta(
        self,
        request,
        respuesta_id: UUID,
    ):
        """
        Anula una respuesta que se encuentra en estado EMITIDA.

        La anulación es irreversible: transiciona la respuesta de EMITIDA a ANULADA.

        El flujo:
        1. Valida que la respuesta existe (404 si no).
        2. Valida que la respuesta está en estado EMITIDA (400 si no).
        3. Transiciona la respuesta a ANULADA.
        4. Retorna la respuesta actualizada.
        """
        respuesta = await self.periodo_orchestrator.anular_respuesta(
            respuesta_id=respuesta_id,
            usuario_id=request.auth.id,
        )

        presenter_sync = sync_to_async(
            RespuestaPresenter.present,
            thread_sensitive=True,
        )
        respuesta_out = await presenter_sync(respuesta)
        return success_response(respuesta_out.model_dump())

    @route.post("/{respuesta_id}/rectificar", response={200: ApiResponse[RespuestaOut]})
    async def rectificar_respuesta(
        self,
        request,
        respuesta_id: UUID,
    ):
        """
        Rectifica una respuesta que se encuentra en estado EMITIDA.

        La rectificación es una corrección formal: transiciona la respuesta de EMITIDA
        a RECTIFICADA.

        El flujo:
        1. Valida que la respuesta existe (404 si no).
        2. Valida que la respuesta está en estado EMITIDA (400 si no).
        3. Transiciona la respuesta a RECTIFICADA.
        4. Retorna la respuesta actualizada.
        """
        respuesta = await self.periodo_orchestrator.rectificar_respuesta(
            respuesta_id=respuesta_id,
            usuario_id=request.auth.id,
        )

        presenter_sync = sync_to_async(
            RespuestaPresenter.present,
            thread_sensitive=True,
        )
        respuesta_out = await presenter_sync(respuesta)
        return success_response(respuesta_out.model_dump())
