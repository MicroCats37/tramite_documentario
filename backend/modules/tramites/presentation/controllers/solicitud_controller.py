"""
SolicitudController — controlador HTTP ligero para creación y consulta de solicitudes.

Solo delega a SolicitudOrchestrator y retorna vía presenter.
Patrón 3: JSON Estricto — sin archivos, payload puro.
Patrón Dual Payload: /crear-completo (FormData + archivos).
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
import json
from uuid import UUID
from datetime import datetime

from asgiref.sync import sync_to_async

from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated
from injector import inject
from ninja import Form, File, Query
from ninja.files import UploadedFile

from core.types import DataForm, parse_form_json
from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.tramites.presentation.schemas.solicitud_in import (
    SolicitudCreateIn,
    SolicitudHibridaCreateIn,
    IncorporarAreaIn,
)
from modules.tramites.presentation.schemas.solicitud_out import SolicitudOut
from modules.tramites.presentation.schemas.solicitud_list_out import (
    SolicitudItemOut,
    SolicitudDetailOut,
    EstadoOperativoOut,
)
from modules.tramites.presentation.presenters.solicitud_presenter import SolicitudPresenter
from modules.tramites.presentation.presenters.solicitud_consulta_presenter import SolicitudConsultaPresenter
from modules.tramites.domain.services.orchestrators.solicitud_orchestrator import SolicitudOrchestrator


def _strip_pydantic(obj):
    """
    Recursively convert Pydantic models in a response dict to plain dicts.
    This is needed because Django's JSONField cannot serialize Pydantic model instances.
    """
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {k: _strip_pydantic(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_strip_pydantic(item) for item in obj]
    return obj


@api_controller("/solicitudes", tags=["Solicitudes"], permissions=[IsAuthenticated])
class SolicitudController:
    """
    Controlador para gestión de solicitudes.

    Endpoints de creación:
    1. Recibe el payload JSON (patrón 3: JSON Estricto)
    2. Delega a SolicitudOrchestrator
    3. Transforma el resultado vía SolicitudPresenter
    4. Retorna la respuesta HTTP

    Endpoints de consulta:
    1. Recibe query params
    2. Delega a SolicitudOrchestrator
    3. Transforma resultado a schema
    4. Retorna la respuesta HTTP
    """

    @inject
    def __init__(self, solicitud_orchestrator: SolicitudOrchestrator):
        self.solicitud_orchestrator = solicitud_orchestrator

    @route.post("/crear", response={200: ApiResponse[SolicitudItemOut]})
    async def crear_solicitud(
        self,
        request,
        payload: SolicitudCreateIn,
    ):
        """
        Crea una nueva solicitud con distribución de áreas.

        Utiliza el patrón JSON Estricto (patrón 3):
        - Payload puro JSON sin archivos
        - Validación automática via Pydantic

        El flujo:
        1. Verifica que el expediente existe y no tiene solicitud asociada.
        2. Crea la Solicitud en estado REGISTRADA (o EN_GESTION si hay áreas).
        3. Crea el historial de estado.
        4. Crea las asignaciones por cada área del payload.
        5. Crea las notificaciones para cada área.

        Retorna SolicitudItemOut con expediente anidado para consistencia
        con list items (frontend cache insertion).
        """
        solicitud = await self.solicitud_orchestrator.crear_solicitud_con_distribucion(
            payload,
            request.auth.id,
        )
        presenter_sync = sync_to_async(
            SolicitudConsultaPresenter.present_list_item,
            thread_sensitive=True,
        )
        return success_response(await presenter_sync(solicitud))

    @route.post("/crear-completo", response={200: ApiResponse[SolicitudItemOut]})
    async def crear_solicitud_completa(
        self,
        request,
        data: Form[DataForm],
        files: File[list[UploadedFile]],
    ):
        """
        Crea una solicitud con expediente y distribución en una sola operación.

        Utiliza el patrón dual payload (FormData + archivos):
        - `data`: JSON string con los campos de la solicitud y expediente
        - `files`: lista de archivos con nombre con formato "token___nombre_real.ext"

        Soporta header `Idempotency-Key` para prevenir duplicados en reintentos.

        El flujo:
        1. Si hay Idempotency-Key, busca resultado cacheado y lo retorna.
        2. Crea el Expediente con sus archivos (transacción atómica).
        3. Crea la Solicitud asociada al expediente.
        4. Crea el historial de estado.
        5. Crea las asignaciones por cada área del payload.
        6. Crea las notificaciones para cada área.
        7. Cachea el resultado con la clave de idempotencia.

        Retorna SolicitudItemOut con expediente anidado para consistencia
        con list items (frontend cache insertion).
        """
        from django.http import JsonResponse

        from modules.tramites.domain.models import IdempotencyKey

        idempotency_key = request.headers.get("Idempotency-Key")

        if idempotency_key:
            cached = await sync_to_async(
                lambda: IdempotencyKey.objects.filter(
                    key=idempotency_key,
                    usuario_id=request.auth.id,
                    endpoint="/solicitudes/crear-completo",
                ).first(),
                thread_sensitive=True,
            )()
            if cached is not None:
                return JsonResponse(cached.result, status=cached.status_code)

        payload = parse_form_json(data.data, files, SolicitudHibridaCreateIn)
        solicitud = await self.solicitud_orchestrator.crear_solicitud_hibrida(
            payload,
            request.auth.id,
        )

        presenter_sync = sync_to_async(
            SolicitudConsultaPresenter.present_list_item,
            thread_sensitive=True,
        )
        result = await presenter_sync(solicitud)
        response = success_response(result)

        if idempotency_key:
            serializable_result = _strip_pydantic(response)
            await sync_to_async(
                lambda: IdempotencyKey.objects.create(
                    key=idempotency_key,
                    usuario_id=request.auth.id,
                    endpoint="/solicitudes/crear-completo",
                    result=serializable_result,
                    status_code=200,
                ),
                thread_sensitive=True,
            )()

        return response

    @route.get("/", response={200: ApiResponse[PaginatedData[SolicitudItemOut]]})
    async def listar_solicitudes(
        self,
        request,
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
        estado: str | None = Query(None, description="Filtrar por estado"),
        prioridad: str | None = Query(None, description="Filtrar por prioridad"),
        area_id: UUID | None = Query(None, description="Filtrar por área"),
        tipo_participacion: str | None = Query(None, description="Filtrar por tipo de participación"),
        periodo_estado: str | None = Query(None, description="Filtrar por estado de período"),
        usuario_id: int | None = Query(None, description="Filtrar por usuario"),
        me: bool = Query(False, description="Filtrar solicitudes donde el usuario participa"),
        sin_participantes: bool = Query(False, description="Filtrar asignaciones sin participantes"),
        con_respuesta: bool = Query(False, description="Filtrar áreas con respuesta emitida"),
        fecha_desde: datetime | None = Query(None, description="Filtrar desde fecha de registro"),
        fecha_hasta: datetime | None = Query(None, description="Filtrar hasta fecha de registro"),
        busqueda: str | None = Query(None, description="Buscar en id_publico, numero_documento, dni, asunto"),
    ):
        """
        Lista solicitudes con filtros y paginación.

        Filtros disponibles:
        - estado: estado de la solicitud
        - prioridad: prioridad del trámite
        - area_id: área asignada
        - tipo_participacion: PRINCIPAL o ADJUNTA
        - periodo_estado: PENDIENTE, EN_GESTION o CERRADO
        - usuario_id: usuario asignado
        - me: true = solo solicitudes donde el usuario autenticado participa
        - sin_participantes: true = áreas sin participantes activos
        - con_respuesta: true = áreas con respuesta emitida
        - fecha_desde/fecha_hasta: rango de fecha de registro
        - busqueda: texto en id_publico, numero_documento, dni, asunto
        """
        result = await self.solicitud_orchestrator.listar_solicitudes(
            page=page,
            page_size=page_size,
            estado=estado,
            prioridad=prioridad,
            area_id=area_id,
            tipo_participacion=tipo_participacion,
            periodo_estado=periodo_estado,
            usuario_id=usuario_id,
            me=me,
            sin_participantes=sin_participantes,
            con_respuesta=con_respuesta,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            busqueda=busqueda,
        )

        items, total, page, page_size, total_pages = result

        presenter_sync = sync_to_async(
            lambda: [
                SolicitudConsultaPresenter.present_list_item(sol)
                for sol in items
            ],
            thread_sensitive=True,
        )
        item_outs = await presenter_sync()

        return success_response(PaginatedData(
            items=item_outs,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ))

    @route.get("/{solicitud_id}/", response={200: ApiResponse[SolicitudDetailOut]})
    @route.get("/{solicitud_id}", response={200: ApiResponse[SolicitudDetailOut]})
    async def obtener_solicitud(
        self,
        request,
        solicitud_id: UUID,
    ):
        """
        Obtiene el detalle integral de una solicitud.

        Consolida:
        - Solicitud (con expediente y asignaciones)
        - Historial global de estados
        - Expediente completo con archivos y antecedentes
        - Por cada asignación: períodos ordenados, participantes, respuestas
        """
        from ninja.errors import HttpError

        solicitud = await sync_to_async(
            self.solicitud_orchestrator.obtener_solicitud_sync,
            thread_sensitive=True,
        )(solicitud_id)

        if solicitud is None:
            raise HttpError(404, "Solicitud no encontrada")

        presenter_sync = sync_to_async(
            SolicitudConsultaPresenter.present_detail,
            thread_sensitive=True,
        )
        detail_out = await presenter_sync(solicitud)

        return success_response(detail_out)

    @route.get("/{solicitud_id}/estado-operativo", response={200: ApiResponse[EstadoOperativoOut]})
    async def estado_operativo(
        self,
        request,
        solicitud_id: UUID,
    ):
        """
        Calcula el resumen operativo sin persistir nada.

        Métricas:
        - total_areas: total de áreas asignadas
        - areas_pendientes: áreas con todos sus períodos en PENDIENTE
        - areas_en_gestion: áreas con al menos un período en EN_GESTION
        - areas_cerradas: áreas con todos sus períodos en CERRADO
        - con_respuesta: áreas que tienen al menos una respuesta emitida
        - sin_participantes: áreas sin participantes activos
        - vencida: fecha_limite < ahora y estado != FINALIZADA
        """
        from ninja.errors import HttpError

        resultado = await self.solicitud_orchestrator.calcular_estado_operativo(solicitud_id)

        if resultado is None:
            raise HttpError(404, "Solicitud no encontrada")

        return success_response(EstadoOperativoOut(**resultado))

    @route.post("/{solicitud_id}/areas", response={200: ApiResponse[SolicitudOut]})
    async def incorporar_area(
        self,
        request,
        solicitud_id: UUID,
        payload: IncorporarAreaIn,
    ):
        """
        Incorpora un área a una solicitud existente.

        Utiliza el patrón JSON Estricto (patrón 3):
        - Payload puro JSON sin archivos

        El flujo:
        1. Valida que la Solicitud existe y no está finalizada/anulada.
        2. Valida que el Área existe y no está ya asignada.
        3. Crea SolicitudAsignacion + SolicitudAsignacionPeriodo (ciclo 1, PENDIENTE).
        4. Si la solicitud estaba en REGISTRADA → transiciona a EN_GESTION.
        5. Crea la notificación para el área.
        """
        solicitud = await self.solicitud_orchestrator.incorporar_area(
            solicitud_id=solicitud_id,
            area_id=payload.area_id,
            tipo_participacion=payload.tipo_participacion,
            observacion=payload.observacion,
            usuario_id=request.auth.id,
        )
        presenter_sync = sync_to_async(
            SolicitudPresenter.present,
            thread_sensitive=True,
        )
        return success_response(await presenter_sync(solicitud))
