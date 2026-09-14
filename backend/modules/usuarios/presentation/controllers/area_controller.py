"""
AreaController — controlador HTTP ligero para consulta de áreas.

Solo retorna áreas activas directo del modelo (consulta pura, sin lógica).
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
from datetime import timedelta

from asgiref.sync import sync_to_async

from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated

from core.responses import ApiResponse, success_response
from modules.usuarios.presentation.schemas.area_schemas import AreaOut
from modules.usuarios.domain.selectors.area_selector import AreaSelector


def _tiempo_respuesta_parts(value: timedelta | None) -> tuple[int | None, int | None]:
    """Compute (dias, horas) integer parts from a timedelta or None."""
    if value is None:
        return None, None
    total_seconds = int(value.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    return days, hours


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

        Retorna id, nombre, descripcion, flag activo y tiempo_respuesta de cada área.
        """
        def _fetch():
            areas = []
            for area in AreaSelector.listar_activas():
                dias, horas = _tiempo_respuesta_parts(area.tiempo_respuesta)
                areas.append(
                    AreaOut(
                        id=area.id,
                        nombre=area.nombre,
                        descripcion=area.descripcion,
                        activo=area.activo,
                        tiempo_respuesta=area.tiempo_respuesta,
                        tiempo_respuesta_dias=dias,
                        tiempo_respuesta_horas=horas,
                    )
                )
            return areas

        areas = await sync_to_async(_fetch, thread_sensitive=True)()
        return success_response(areas)