"""
TipoDocumentoController — controlador HTTP ligero para consulta de tipos de documento.

Solo retorna tipos de documento directo del modelo (consulta pura, sin lógica).
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
from asgiref.sync import sync_to_async

from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated

from core.responses import ApiResponse, success_response
from modules.tramites.presentation.schemas.tipo_documento_out import TipoDocumentoOut
from modules.tramites.domain.selectors.tipo_documento_selector import TipoDocumentoSelector


@api_controller("/tipos-documento", tags=["Tipos de Documento"], permissions=[IsAuthenticated])
class TipoDocumentoController:
    """
    Controlador para consulta de tipos de documento.

    Endpoints:
    - GET /: Lista todos los tipos de documento disponibles
    """

    @route.get("/", response={200: ApiResponse[list[TipoDocumentoOut]]})
    async def listar_tipos_documento(self, request):
        """
        Lista todos los tipos de documento disponibles.

        Retorna id, nombre y descripcion de cada tipo de documento.
        """
        def _fetch():
            return [
                TipoDocumentoOut(
                    id=td.id,
                    nombre=td.nombre,
                    descripcion=td.descripcion,
                )
                for td in TipoDocumentoSelector.listar_todos()
            ]

        tipos = await sync_to_async(_fetch, thread_sensitive=True)()
        return success_response(tipos)
