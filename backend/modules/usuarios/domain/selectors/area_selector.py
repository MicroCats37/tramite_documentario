"""
AreaSelector — consultas de dominio para Area.

Sigue el patrón selector del contrato de arquitectura (django-app-architecture-contract §4.12).
"""
from uuid import UUID

from modules.usuarios.domain.models.area import Area


class AreaSelector:
    """
    Selector para consultas de áreas.

    Mantiene las queries en una capa de dominio en lugar del controller,
    permitiendo reutilización y testabilidad.
    """

    @staticmethod
    def listar_activas():
        """
        Lista todas las áreas activas ordenadas por nombre.

        Returns:
            QuerySet de Area filtradas por activo=True y ordenadas
        """
        return Area.objects.filter(activo=True).order_by("nombre")

    @staticmethod
    def get_by_id(area_id: UUID) -> Area | None:
        """
        Obtiene un área por ID.

        Args:
            area_id: UUID del área

        Returns:
            Area o None si no existe
        """
        try:
            return Area.objects.get(id=area_id)
        except Area.DoesNotExist:
            return None
