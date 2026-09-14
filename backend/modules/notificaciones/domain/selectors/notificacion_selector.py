"""
NotificacionSelector — consultas especializadas para el módulo de notificaciones.

Sigue el patrón de arquitectura: el selector carga datos del ORM con las relaciones
necesarias; el presenter transforma el resultado a esquema HTTP.
"""
from uuid import UUID

from django.db.models import Prefetch

from modules.notificaciones.domain.models import Notificacion, NotificacionUsuario


class NotificacionSelector:
    """
    Selector para consultas de Notificacion.

    Carga notificaciones con todas las relaciones necesarias para presentar
    el detalle contextual (SOLICITUD, SISTEMA u otros ámbitos).
    """

    @staticmethod
    def obtener_detalle(notificacion_id: UUID, usuario_id: int) -> Notificacion | None:
        """
        Carga una notificación con todas las relaciones necesarias para el detalle.

        Incluye:
        - generada_por (usuario que generó la notificación)
        - usuarios_notificados + interacciones del usuario actual
        - areas_notificadas + área
        - contexto_solicitud + solicitud + expediente (para SOLICITUD)
        - contexto_solicitud + periodo (para contexto de período)

        Args:
            notificacion_id: UUID de la notificación a cargar.
            usuario_id: ID del usuario autenticado (para filtrar su interacción).

        Returns:
            Instancia de Notificacion con relaciones prefetched, o None si no existe.
        """
        try:
            mis_interacciones = NotificacionUsuario.objects.filter(usuario_id=usuario_id)
            return (
                Notificacion.objects
                .select_related("generada_por")
                .prefetch_related(
                    Prefetch("usuarios_notificados", queryset=mis_interacciones),
                    Prefetch("areas_notificadas__area"),
                    Prefetch("contexto_solicitud__solicitud__expediente"),
                    Prefetch("contexto_solicitud__periodo"),
                )
                .get(id=notificacion_id)
            )
        except Notificacion.DoesNotExist:
            return None
