"""
ExpedienteController — controlador HTTP ligero para registro y consulta de expedientes.

Solo delega a ExpedienteOrchestrator y retorna vía presenter.
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
from uuid import UUID

from asgiref.sync import sync_to_async

from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated
from injector import inject
from ninja import Form, File, Query
from ninja.files import UploadedFile

from core.types import DataForm, parse_form_json
from core.responses import ApiResponse, success_response
from core.pagination import PaginatedData
from modules.tramites.presentation.schemas.expediente_in import ExpedienteCreateIn
from modules.tramites.presentation.schemas.expediente_list_out import (
    ExpedienteItemOut,
    ExpedienteDetailOut,
)
from modules.tramites.presentation.presenters.expediente_presenter import ExpedientePresenter
from modules.tramites.presentation.presenters.expediente_consulta_presenter import ExpedienteConsultaPresenter
from modules.tramites.domain.services.orchestrators.expediente_orchestrator import ExpedienteOrchestrator


@api_controller("/expedientes", tags=["Expedientes"], permissions=[IsAuthenticated])
class ExpedienteController:
    """
    Controlador para gestión de expedientes.

    Endpoints de creación:
    1. Recibe el payload via FormData (patrón dual payload)
    2. Delega a ExpedienteOrchestrator
    3. Transforma el resultado vía ExpedientePresenter
    4. Retorna la respuesta HTTP

    Endpoints de consulta:
    1. Recibe query params
    2. Delega a ExpedienteOrchestrator (query methods)
    3. Transforma resultado a schema
    4. Retorna la respuesta HTTP
    """

    @inject
    def __init__(self, expediente_orchestrator: ExpedienteOrchestrator):
        self.expediente_orchestrator = expediente_orchestrator

    @route.post("/crear", response={200: ApiResponse[ExpedienteItemOut]})
    async def crear_expediente(
        self,
        request,
        data: Form[DataForm],
        files: File[list[UploadedFile]],
    ):
        """
        Registra un nuevo expediente con archivos adjuntos.

        Utiliza el patrón dual payload:
        - `data`: JSON string con los campos del expediente (serializado como DataForm)
        - `files`: lista de archivos con nombre con formato "token___nombre_real.ext"

        El token se usa para hidratar los campos UploadedFile en el schema.
        """
        payload = parse_form_json(data.data, files, ExpedienteCreateIn)
        expediente = await self.expediente_orchestrator.crear_expediente(
            payload,
            request.auth.id,
        )
        presenter_sync = sync_to_async(
            ExpedientePresenter.present,
            thread_sensitive=True,
        )
        return success_response(await presenter_sync(expediente))

    @route.get("/", response={200: ApiResponse[PaginatedData[ExpedienteItemOut]]})
    async def listar_expedientes(
        self,
        request,
        page: int = Query(1, ge=1, description="Número de página"),
        page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
        busqueda: str | None = Query(None, description="Texto a buscar"),
        año: int | None = Query(None, description="Año de registro"),
    ):
        """
        Lista expedientes con filtros y paginación.

        Filtros disponibles:
        - busqueda: busca en id_publico, numero_documento, dni, ruc, nombres, razon_social, asunto
        - año: filtra por año de fecha_registro
        """
        result = await self.expediente_orchestrator.listar_expedientes(
            page=page,
            page_size=page_size,
            busqueda=busqueda,
            año=año,
        )

        items, total, page, page_size, total_pages = result

        item_outs = [
            ExpedienteConsultaPresenter.present_list_item(exp)
            for exp in items
        ]

        return success_response(PaginatedData(
            items=item_outs,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ))

    @route.get("/{expediente_id}", response={200: ApiResponse[ExpedienteDetailOut]})
    async def obtener_expediente(
        self,
        request,
        expediente_id: UUID,
    ):
        """
        Obtiene el detalle de un expediente por ID.

        Incluye archivos, antecedentes, datos del creador y solicitud asociada (si existe).
        """
        from ninja.errors import HttpError

        expediente = await self.expediente_orchestrator.obtener_expediente(expediente_id)

        if expediente is None:
            raise HttpError(404, "Expediente no encontrado")

        detail_out = ExpedienteConsultaPresenter.present_detail(expediente)

        return success_response(detail_out)