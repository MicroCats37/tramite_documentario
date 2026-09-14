"""
TipoDocumentoSelector — consultas de dominio para TipoDocumento.

Sigue el patrón selector del contrato de arquitectura (django-app-architecture-contract §4.12).
"""
from uuid import UUID

from modules.tramites.domain.models.tipo_documento import TipoDocumento


class TipoDocumentoSelector:
    """
    Selector para consultas de tipos de documento.

    Mantiene las queries en una capa de dominio en lugar del controller,
    permitiendo reutilización y testabilidad.
    """

    @staticmethod
    def listar_todos():
        """
        Lista todos los tipos de documento ordenados por nombre.

        A diferencia de AreaSelector, no filtra por estado (activo/inactivo)
        porque TipoDocumento es un catálogo de solo lectura sin flag activo.

        Returns:
            QuerySet de TipoDocumento ordenados por nombre
        """
        return TipoDocumento.objects.all().order_by("nombre")

    @staticmethod
    def get_by_id(tipo_documento_id: UUID) -> TipoDocumento | None:
        """
        Obtiene un tipo de documento por ID.

        Args:
            tipo_documento_id: UUID del tipo de documento

        Returns:
            TipoDocumento o None si no existe
        """
        try:
            return TipoDocumento.objects.get(id=tipo_documento_id)
        except TipoDocumento.DoesNotExist:
            return None
