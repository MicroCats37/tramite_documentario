"""
AreaController — controlador HTTP ligero para consulta de áreas.

Solo retorna áreas activas directo del modelo (consulta pura, sin lógica).
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
from asgiref.sync import sync_to_async

from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated

from core.responses import ApiResponse, success_response
from modules.usuarios.presentation.schemas.area_schemas import AreaOut
from modules.usuarios.domain.selectors.area_selector import AreaSelector


@api_controller("/areas", tags=["Áreas"], permissions=[IsAuthenticated])
class AreaController:
    """
    Controlador para consulta de áreas activas.

    Endpoints:
    - GET /: Lista todas las áreas activas
    """

    @route.get("/", response={200: ApiResponse[list[AreaOut]]})
    async def listar_areas(self, request):
        """
        Lista todas las áreas activas.

        Retorna id, nombre, descripcion y flag activo de cada área.
        """
        def _fetch():
            return [
                AreaOut(
                    id=area.id,
                    nombre=area.nombre,
                    descripcion=area.descripcion,
                    activo=area.activo,
                )
                for area in AreaSelector.listar_activas()
            ]

        areas = await sync_to_async(_fetch, thread_sensitive=True)()
        return success_response(areas)