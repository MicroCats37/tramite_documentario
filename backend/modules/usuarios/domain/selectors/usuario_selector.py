"""
UsuarioSelector — consultas de dominio para Usuario.
"""
from uuid import UUID

from django.db.models import Q

from modules.usuarios.domain.models import Usuario


class UsuarioSelector:
    """
    Selector para consultas de usuarios.
    """

    @staticmethod
    def get_by_id(usuario_id: UUID) -> Usuario | None:
        """
        Obtiene un usuario por ID.

        Args:
            usuario_id: UUID del usuario

        Returns:
            Usuario o None si no existe
        """
        try:
            return Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            return None
