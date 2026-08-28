"""
PeriodoController — controlador HTTP ligero para operaciones de períodos de asignación.

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
from modules.asignaciones.presentation.schemas.periodo_in import (
    AgregarUsuarioPeriodoIn,
    CambiarParticipacionIn,
    CrearRespuestaBorradorIn,
    FinalizarPeriodoIn,
    MarcarAsignacionErroneaIn,
)
from modules.asignaciones.presentation.schemas.respuesta_out import RespuestaOut
from modules.asignaciones.presentation.presenters.respuesta_presenter import (
    RespuestaPresenter,
)
from modules.tramites.presentation.presenters.solicitud_presenter import (
    SolicitudPresenter,
)


@api_controller("/periodos", tags=["Períodos"], permissions=[IsAuthenticated])
class PeriodoController:
    """
    Controlador para gestión de períodos de asignación.

    Endpoints:
    1. POST /{periodo_id}/iniciar-gestion — inicia la gestión de un período
    2. POST /{periodo_id}/tomar — el usuario toma el período asignándose como participante
    3. POST /{periodo_id}/usuarios — asigna un usuario como participante a un período
    4. POST /{periodo_id}/finalizar — cierra un período
    """

    @inject
    def __init__(self, periodo_orchestrator: PeriodoOrchestrator):
        self.periodo_orchestrator = periodo_orchestrator

    @route.post("/{periodo_id}/iniciar-gestion", response={200: ApiResponse[dict]})
    async def iniciar_gestion(
        self,
        request,
        periodo_id: UUID,
    ):
        """
        Inicia la gestión de un período que se encuentra en estado PENDIENTE.

        No requiere body — el ID del período viene en la URL.

        El flujo:
        1. Valida que el período existe y está en estado PENDIENTE.
        2. Transiciona el período a EN_GESTION.
        3. Registra el cambio en SolicitudAsignacionPeriodoEstadoHistorial.
        4. Retorna la solicitud actualizada con todas sus asignaciones.
        """
        periodo = await self.periodo_orchestrator.iniciar_gestion(
            periodo_id=periodo_id,
            usuario_id=request.auth.id,
        )

        # Presentar el período → solicitar presenter
        # El período tiene asignacion.solicitud precargada
        presenter_sync = sync_to_async(
            SolicitudPresenter.present,
            thread_sensitive=True,
        )
        solicitud_out = await presenter_sync(periodo.asignacion.solicitud)
        return success_response(solicitud_out.model_dump())

    @route.post("/{periodo_id}/tomar", response={200: ApiResponse[dict]})
    async def tomar_periodo(
        self,
        request,
        periodo_id: UUID,
    ):
        """
        El usuario toma el período: se asigna a sí mismo como participante
        y transiciona el período de PENDIENTE a EN_GESTION.

        El flujo:
        1. Valida que el período existe y está en estado PENDIENTE.
        2. Crea el registro SolicitudAsignacionUsuario para el usuario.
        3. Transiciona el período a EN_GESTION.
        4. Registra el cambio en SolicitudAsignacionPeriodoEstadoHistorial.
        5. Retorna la solicitud actualizada con todas sus asignaciones.
        """
        periodo = await self.periodo_orchestrator.tomar_periodo(
            periodo_id=periodo_id,
            usuario_id=request.auth.id,
        )

        presenter_sync = sync_to_async(
            SolicitudPresenter.present,
            thread_sensitive=True,
        )
        solicitud_out = await presenter_sync(periodo.asignacion.solicitud)
        return success_response(solicitud_out.model_dump())

    @route.post("/{periodo_id}/usuarios", response={200: ApiResponse[dict]})
    async def agregar_usuario(
        self,
        request,
        periodo_id: UUID,
        payload: AgregarUsuarioPeriodoIn,
    ):
        """
        Asigna un usuario como participante a un período existente.

        El usuario autenticado asigna a otro usuario (payload.usuario_id) como participante
        del período. No cambia el estado del período.

        El flujo:
        1. Valida que el período existe y no está CERRADO.
        2. Valida que el usuario a asignar existe.
        3. Valida que el usuario a asignar no esté ya activamente asignado al período.
        4. Crea el registro SolicitudAsignacionUsuario.
        5. Retorna la solicitud actualizada con todas sus asignaciones.
        """
        periodo = await self.periodo_orchestrator.agregar_usuario_periodo(
            periodo_id=periodo_id,
            usuario_id=request.auth.id,
            usuario_a_asignar_id=payload.usuario_id,
            rol=payload.rol,
        )

        presenter_sync = sync_to_async(
            SolicitudPresenter.present,
            thread_sensitive=True,
        )
        solicitud_out = await presenter_sync(periodo.asignacion.solicitud)
        return success_response(solicitud_out.model_dump())

    @route.post("/{periodo_id}/finalizar", response={200: ApiResponse[dict]})
    async def finalizar_periodo(
        self,
        request,
        periodo_id: UUID,
        payload: FinalizarPeriodoIn | None = None,
    ):
        """
        Finaliza un período de asignación, transicionándolo a CERRADO.

        Por defecto tipo_cierre es FINALIZADO. El payload es opcional
        (si no se envía, se usan los defaults).

        El flujo:
        1. Valida que el período existe y no está ya CERRADO.
        2. Transiciona el período a CERRADO (fecha_fin, finalizado_por, tipo_cierre).
        3. Registra el cambio en SolicitudAsignacionPeriodoEstadoHistorial.
        4. Retorna la solicitud actualizada con todas sus asignaciones.

        Nota: Esta implementación NO valida que exista una respuesta EMITIDA
        antes de cerrar. La regla "cada área debe registrar una respuesta formal
        antes de finalizar" fue diferida para discusión al final. Se documenta
        como caveat en el apply-progress.
        """
        if payload is None:
            payload = FinalizarPeriodoIn()

        periodo = await self.periodo_orchestrator.finalizar_periodo(
            periodo_id=periodo_id,
            usuario_id=request.auth.id,
            tipo_cierre=payload.tipo_cierre,
            motivo_cierre=payload.motivo_cierre,
            observacion=payload.observacion,
        )

        presenter_sync = sync_to_async(
            SolicitudPresenter.present,
            thread_sensitive=True,
        )
        solicitud_out = await presenter_sync(periodo.asignacion.solicitud)
        return success_response(solicitud_out.model_dump())

    @route.post("/{periodo_id}/marcar-asignacion-erronea", response={200: ApiResponse[dict]})
    async def marcar_asignacion_erronea(
        self,
        request,
        periodo_id: UUID,
        payload: MarcarAsignacionErroneaIn | None = None,
    ):
        """
        Marca un período como asignación errónea, transicionándolo a CERRADO
        con tipo_cierre=ASIGNACION_ERRONEA.

        El payload es opcional (si no se envía, se usa solo el tipo de cierre).

        El flujo:
        1. Valida que el período existe y no está ya CERRADO.
        2. Transiciona el período a CERRADO con tipo_cierre=ASIGNACION_ERRONEA.
        3. Registra el cambio en SolicitudAsignacionPeriodoEstadoHistorial.
        4. Retorna la solicitud actualizada con todas sus asignaciones.
        """
        if payload is None:
            payload = MarcarAsignacionErroneaIn()

        periodo = await self.periodo_orchestrator.marcar_asignacion_erronea(
            periodo_id=periodo_id,
            usuario_id=request.auth.id,
            motivo_cierre=payload.motivo_cierre,
            observacion=payload.observacion,
        )

        presenter_sync = sync_to_async(
            SolicitudPresenter.present,
            thread_sensitive=True,
        )
        solicitud_out = await presenter_sync(periodo.asignacion.solicitud)
        return success_response(solicitud_out.model_dump())

    @route.post("/{periodo_id}/cambiar-participacion", response={200: ApiResponse[dict]})
    async def cambiar_participacion(
        self,
        request,
        periodo_id: UUID,
        payload: CambiarParticipacionIn,
    ):
        """
        Cambia el tipo de participación de un período (PRINCIPAL ↔ ADJUNTA).

        El flujo:
        1. Valida que el período existe.
        2. Valida que el nuevo tipo es PRINCIPAL o ADJUNTA.
        3. Valida que el período no está CERRADO.
        4. Valida que el nuevo tipo es diferente al actual.
        5. Cambia tipo_participacion del período.
        6. Registra el cambio en SolicitudAsignacionPeriodoEstadoHistorial
           con origen=CAMBIO_PARTICIPACION.
        7. Retorna la solicitud actualizada con todas sus asignaciones.
        """
        periodo = await self.periodo_orchestrator.cambiar_participacion(
            periodo_id=periodo_id,
            usuario_id=request.auth.id,
            nuevo_tipo=payload.tipo_participacion,
        )

        presenter_sync = sync_to_async(
            SolicitudPresenter.present,
            thread_sensitive=True,
        )
        solicitud_out = await presenter_sync(periodo.asignacion.solicitud)
        return success_response(solicitud_out.model_dump())

    @route.post("/{periodo_id}/respuestas", response={200: ApiResponse[RespuestaOut]})
    async def crear_respuesta_borrador(
        self,
        request,
        periodo_id: UUID,
        payload: CrearRespuestaBorradorIn,
    ):
        """
        Crea una respuesta en estado BORRADOR para un período.

        El borrador puede crearse mientras el período esté abierto (PENDIENTE o EN_GESTION).
        El estado es siempre BORRADOR — la emisión se hace en un endpoint posterior.

        El flujo:
        1. Valida que el período existe (404 si no).
        2. Valida que el período no está CERRADO (409 si ya cerrado).
        3. Valida que el tipo_respuesta es válido (400 si no).
        4. Crea SolicitudAsignacionRespuesta con estado=BORRADOR.
        5. Retorna la respuesta creada.
        """
        respuesta = await self.periodo_orchestrator.crear_respuesta_borrador(
            periodo_id=periodo_id,
            usuario_id=request.auth.id,
            tipo_respuesta=payload.tipo_respuesta,
            contenido=payload.contenido,
            archivo=payload.archivo,
            observacion=payload.observacion,
        )

        presenter_sync = sync_to_async(
            RespuestaPresenter.present,
            thread_sensitive=True,
        )
        respuesta_out = await presenter_sync(respuesta)
        return success_response(respuesta_out.model_dump())

    @route.get("/{periodo_id}/respuestas", response={200: ApiResponse[list[RespuestaOut]]})
    async def listar_respuestas_periodo(
        self,
        request,
        periodo_id: UUID,
    ):
        """
        Lista las respuestas de un período, ordenadas por fecha de creación descendente.

        El flujo:
        1. Valida que el período existe (404 si no).
        2. Consulta todas las respuestas del período.
        3. Retorna la lista de respuestas.

        No requiere que el usuario sea participante activo — cualquier usuario
        autenticado puede consultar las respuestas del período.
        """
        respuestas = await self.periodo_orchestrator.listar_respuestas(
            periodo_id=periodo_id,
        )

        presenter_sync = sync_to_async(
            RespuestaPresenter.present,
            thread_sensitive=True,
        )
        respuestas_out = [await presenter_sync(r) for r in respuestas]
        return success_response([r.model_dump() for r in respuestas_out])
