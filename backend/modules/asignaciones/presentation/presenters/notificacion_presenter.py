"""
NotificacionPresenter — transforma datos de consulta de Notificacion a esquemas HTTP.

Extrae la lógica de presentación de NotificacionController.listar_notificaciones y
obtener_notificacion, siguiendo el contrato de controllers-delgados (薄).
"""
from asgiref.sync import sync_to_async
from uuid import UUID

from modules.asignaciones.domain.models import Notificacion, NotificacionUsuario
from modules.asignaciones.presentation.schemas.notificacion_schemas import (
    NotificacionItemOut,
    NotificacionDetailOut,
    InteraccionOut,
)


class NotificacionPresenter:
    """
    Presenter para consultas (listado y detalle) de Notificacion.

    Mantiene la forma de la respuesta JSON - solo mueve la construcción
    de los schemas Out desde el controller hacia acá.
    """

    @staticmethod
    def present_list_item(
        notif: Notificacion,
        usuario_id: int,
    ) -> NotificacionItemOut:
        """
        Construye un NotificacionItemOut desde una entidad Notificacion (listado).

        Args:
            notif: Entidad Notificacion con usuarios_notificados prefeteched
            usuario_id: ID del usuario autenticado (para buscar su interacción)

        Returns:
            NotificacionItemOut listo para PaginatedData
        """
        # Obtener la interacción del usuario actual (ya prefetched)
        interacciones_usuario = [
            iu for iu in notif.usuarios_notificados.all()
            if iu.usuario_id == usuario_id
        ]
        interaccion = interacciones_usuario[0] if interacciones_usuario else None

        vista = interaccion.vista_at is not None if interaccion else False
        abierta = interaccion.abierta_at is not None if interaccion else False
        descartada = interaccion.descartada_at is not None if interaccion else False
        interactuada = vista or abierta or descartada

        # Obtener id_publico del expediente si existe
        expediente_id_publico = None
        if hasattr(notif, "solicitud") and notif.solicitud and hasattr(notif.solicitud, "expediente"):
            expediente_id_publico = notif.solicitud.expediente.id_publico

        return NotificacionItemOut(
            id=notif.id,
            tipo=notif.tipo,
            titulo=notif.titulo,
            mensaje=notif.mensaje,
            fecha_evento=notif.fecha_evento,
            solicitud_id=notif.solicitud_id if hasattr(notif, "solicitud") else None,
            expediente_id_publico=expediente_id_publico,
            area_nombre=notif.area.nombre if notif.area else "",
            periodo_id=notif.periodo_id,
            interactuada=interactuada,
            vista=vista,
            abierta=abierta,
            descartada=descartada,
        )

    @staticmethod
    async def present_detail(
        notif: Notificacion,
        usuario_id: int,
    ) -> NotificacionDetailOut:
        """
        Construye un NotificacionDetailOut desde una entidad Notificacion (detalle).

        Incluye contexto (solicitud, expediente, área, período) e interacciones
        del usuario autenticado.

        Args:
            notif: Entidad Notificacion con relaciones eager-loaded
            usuario_id: ID del usuario autenticado

        Returns:
            NotificacionDetailOut listo para respuesta HTTP
        """
        # Contexto
        area_id = notif.area_id if notif.area else None
        area_nombre = notif.area.nombre if notif.area else None
        solicitud_id = notif.solicitud_id if hasattr(notif, "solicitud") and notif.solicitud else None
        expediente_id_publico = None
        expediente_asunto = None
        if hasattr(notif, "solicitud") and notif.solicitud and hasattr(notif.solicitud, "expediente"):
            expediente_id_publico = notif.solicitud.expediente.id_publico
            expediente_asunto = notif.solicitud.expediente.asunto

        periodo_id = notif.periodo_id

        # Generada por
        generada_por_nombres = None
        if notif.generada_por:
            generada_por_nombres = f"{notif.generada_por.nombres or ''} {notif.generada_por.apellidos or ''}".strip()

        # Interacciones del usuario actual (query ORM sync envuelta en sync_to_async)
        iu_qs = await sync_to_async(
            lambda: list(notif.usuarios_notificados.filter(usuario_id=usuario_id)),
            thread_sensitive=True,
        )()
        interacciones = [
            InteraccionOut(
                usuario_id=iu.usuario_id,
                vista_at=iu.vista_at,
                abierta_at=iu.abierta_at,
                descartada_at=iu.descartada_at,
            )
            for iu in iu_qs
        ]

        return NotificacionDetailOut(
            id=notif.id,
            tipo=notif.tipo,
            titulo=notif.titulo,
            mensaje=notif.mensaje,
            estado=notif.estado,
            fecha_evento=notif.fecha_evento,
            generada_por_nombres=generada_por_nombres,
            area_id=area_id,
            area_nombre=area_nombre,
            solicitud_id=solicitud_id,
            expediente_id_publico=expediente_id_publico,
            expediente_asunto=expediente_asunto,
            periodo_id=periodo_id,
            interacciones=interacciones,
        )
