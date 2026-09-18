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
from modules.tramites.presentation.schemas.solicitud_respuesta_in import (
    FinalizarSolicitudIn,
)
from modules.tramites.presentation.schemas.solicitud_respuesta_out import (
    SolicitudRespuestaFinalizarOut,
)
from modules.tramites.presentation.schemas.solicitud_trazabilidad_out import (
    SolicitudTrazabilidadOut,
)
from modules.tramites.presentation.presenters.solicitud_presenter import SolicitudPresenter
from modules.tramites.presentation.presenters.solicitud_consulta_presenter import SolicitudConsultaPresenter
from modules.tramites.presentation.presenters.solicitud_respuesta_presenter import (
    SolicitudRespuestaPresenter,
)
from modules.tramites.presentation.presenters.solicitud_trazabilidad_presenter import (
    SolicitudTrazabilidadPresenter,
)
from modules.tramites.domain.services.orchestrators.solicitud_orchestrator import SolicitudOrchestrator
from modules.tramites.domain.services.orchestrators.solicitud_respuesta_orchestrator import (
    SolicitudRespuestaOrchestrator,
)
from modules.notificaciones.domain.selectors.notificacion_selector import NotificacionSelector
from modules.notificaciones.presentation.presenters.notificacion_presenter import NotificacionPresenter
from modules.notificaciones.presentation.schemas.notificacion_schemas import NotificacionDetalleOut


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
    def __init__(
        self,
        solicitud_orchestrator: SolicitudOrchestrator,
        respuesta_orchestrator: SolicitudRespuestaOrchestrator,
    ):
        self.solicitud_orchestrator = solicitud_orchestrator
        self.respuesta_orchestrator = respuesta_orchestrator

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
        mis_areas: bool = Query(False, description="Filtrar solicitudes de áreas donde el usuario tiene asignación vigente"),
        solo_principal: bool = Query(False, description="Filtrar solo áreas PRINCIPAL (requiere mis_areas=true)"),
        creadas_por_mi: bool = Query(False, description="Filtrar solicitudes creadas por el usuario autenticado"),
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
        - mis_areas: true = solo solicitudes con área asignada vigente donde el usuario tiene asignación activa
        - solo_principal: true = solo áreas PRINCIPAL (solo válido con mis_areas=true)
        - creadas_por_mi: true = solo solicitudes creadas por el usuario autenticado
        - sin_participantes: true = áreas sin participantes activos
        - con_respuesta: true = áreas con respuesta emitida
        - fecha_desde/fecha_hasta: rango de fecha de registro
        - busqueda: texto en id_publico, numero_documento, dni, asunto
        """
        # Validation: solo_principal requires mis_areas
        if solo_principal and not mis_areas:
            from ninja.errors import HttpError
            raise HttpError(400, "solo_principal=true requiere mis_areas=true")

        result = await self.solicitud_orchestrator.listar_solicitudes(
            page=page,
            page_size=page_size,
            estado=estado,
            prioridad=prioridad,
            area_id=area_id,
            tipo_participacion=tipo_participacion,
            periodo_estado=periodo_estado,
            usuario_id=usuario_id if usuario_id is not None else request.auth.id,
            me=me,
            mis_areas=mis_areas,
            solo_principal=solo_principal,
            creadas_por_mi=creadas_por_mi,
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

    @route.get("/notificaciones/{notificacion_id}", response={200: ApiResponse[NotificacionDetalleOut]})
    async def obtener_notificacion_desde_solicitud(
        self,
        request,
        notificacion_id: UUID,
    ):
        """
        Obtiene el detalle de una notificación en contexto de solicitud.

        Endpoint owned por el módulo tramites — listo para pantallas modulares futuras
        que consuman notificaciones desde el contexto de una solicitud.

        Usa el mismo selector y presenter que GET /notificaciones/{id}/detalle:
        - NotificacionSelector.obtener_detalle() para cargar datos
        - NotificacionPresenter.present_detail_solicitud() para transformar

        Retorna NotificacionDetalleOut con expediente y período como objetos anidados.
        """
        from ninja.errors import HttpError

        usuario_id = request.auth.id

        notif = await sync_to_async(
            NotificacionSelector.obtener_detalle,
            thread_sensitive=True,
        )(notificacion_id, usuario_id)

        if notif is None:
            raise HttpError(404, "Notificación no encontrada")

        detail_out = await sync_to_async(
            lambda: NotificacionPresenter.present_detail_solicitud(notif, usuario_id),
            thread_sensitive=True,
        )()

        return success_response(detail_out)

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

    @route.post("/{solicitud_id}/finalizar", response={200: ApiResponse[SolicitudRespuestaFinalizarOut]})
    async def finalizar_solicitud(
        self,
        request,
        solicitud_id: UUID,
        data: Form[DataForm],
        files: File[list[UploadedFile]],
    ):
        """
        Emite una respuesta formal a una Solicitud, opcionalmente cerrándola.

        Utiliza el patrón dual payload (FormData + archivos):
        - `data`: JSON string con los campos de la respuesta
        - `files`: lista de archivos con nombre con formato "token___nombre_real.ext"

        El flujo:
        1. Valida que la Solicitud existe y no está FINALIZADA/ANULADA.
        2. Infiere area/periodo del contexto del usuario autenticado.
        3. Obtiene o crea la conversación vinculada.
        4. Crea Mensaje(tipo=SISTEMA) con los archivos adjuntos.
        5. Crea SolicitudRespuesta vinculada.
        6. Si es_final=True: transiciona Solicitud a FINALIZADA y cierra conversación.
        7. Emite notificación RESPUESTA_FINAL al área y al creador de la solicitud.

        Returns:
            SolicitudRespuestaFinalizarOut con la respuesta creada,
            el estado de la solicitud, y la conversación.
        """
        from django.http import JsonResponse

        from modules.tramites.presentation.schemas.solicitud_respuesta_in import (
            FinalizarSolicitudIn,
        )

        payload = parse_form_json(data.data, files, FinalizarSolicitudIn)

        # Construir archivos_data desde el payload hidratado por parse_form_json.
        # Cada archivo en payload.archivos ya tiene el campo 'archivo' hidratado
        # con el UploadedFile real (token reemplazado por el archivo).
        archivos_data = None
        if payload.archivos:
            archivos_data = [
                {
                    "archivo": a.archivo,
                    "nombre_original": a.nombre_original,
                    "mime_type": a.mime_type,
                    "tamano_bytes": a.tamano_bytes,
                }
                for a in payload.archivos
            ]

        # El endpoint /finalizar SEMANTICAMENTE siempre finaliza. No depende del
        # flag es_final del payload (que el frontend nunca envía, defaults a False).
        # Forzamos es_final=True para garantizar cierre de periodos, conversación
        # y transición a FINALIZADA.
        resultado = await self.respuesta_orchestrator.emitir_respuesta_final(
            solicitud_id=solicitud_id,
            usuario_id=request.auth.id,
            tipo_respuesta=payload.tipo_respuesta,
            contenido=payload.contenido,
            es_final=True,
            archivos_data=archivos_data,
        )

        # Obtener estado actual de la solicitud después de la operación
        from modules.tramites.domain.models import Solicitud
        from modules.tramites.domain.constants import EstadoSolicitud

        solicitud_obj = await sync_to_async(
            lambda: Solicitud.objects.get(id=solicitud_id),
            thread_sensitive=True,
        )()
        solicitud_estado = solicitud_obj.estado
        # Usar estado real de la DB, no payload.es_final (que siempre es False
        # desde el frontend). Si la solicitud quedó FINALIZADA, usar fecha_cierre.
        fecha_cierre = (
            solicitud_obj.fecha_cierre
            if solicitud_estado == EstadoSolicitud.FINALIZADA
            else None
        )

        presenter_out = sync_to_async(
            SolicitudRespuestaPresenter.present_finalizar,
            thread_sensitive=True,
        )
        out = await presenter_out(
            resultado=resultado,
            solicitud_estado=solicitud_estado,
            fecha_cierre=fecha_cierre,
            conversacion_id=resultado.conversacion_id,
        )

        return success_response(out)

    @route.get("/{solicitud_id}/trazabilidad", response={200: ApiResponse[SolicitudTrazabilidadOut]})
    async def obtener_trazabilidad(
        self,
        request,
        solicitud_id: UUID,
    ):
        """
        Obtiene el grafo completo de trazabilidad operativa de una solicitud.

        Incluye:
        - Historial global de estados de la solicitud
        - Todas las asignaciones con áreas y períodos ordenados por ciclo
        - Participantes y respuestas por período
        - Timeline cronológico derivado del grafo

        No requiere que el usuario pertenezca al área — la trazabilidad
        es visible para cualquier usuario con acceso a la solicitud.
        """
        from ninja.errors import HttpError

        solicitud = await sync_to_async(
            self.solicitud_orchestrator.obtener_trazabilidad_sync,
            thread_sensitive=True,
        )(solicitud_id)

        if solicitud is None:
            raise HttpError(404, "Solicitud no encontrada")

        presenter_sync = sync_to_async(
            SolicitudTrazabilidadPresenter.present_trazabilidad,
            thread_sensitive=True,
        )
        trazabilidad_out = await presenter_sync(solicitud)

        return success_response(trazabilidad_out)
