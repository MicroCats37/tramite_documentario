"""
ConversacionPresenter — transforma resultados del dominio a esquemas HTTP.

Responsabilidad: construir los schemas HTTP (Out) desde las entidades
de dominio o resultados del servicio. Mantiene el controller delgado.
"""

import uuid
from datetime import datetime
from typing import Optional

from django.conf import settings

from core_application.storage.resolvers import resolve_public_url
from modules.conversaciones.domain.constants import EstadoConversacion
from modules.conversaciones.domain.models import Conversacion, Mensaje
from modules.conversaciones.domain.results.mensaje_results import (
    ArchivoAdjuntoResult,
    MencionResult,
    MensajeConAdjuntosResult,
)
from modules.conversaciones.presentation.schemas.conversacion_schemas import (
    ArchivoAdjuntoOut,
    ConversacionCerrarIn,
    ConversacionCreateIn,
    ConversacionOut,
    ConversacionDetailOut,
    MencionOut,
    MensajeOut,
)


class ConversacionPresenter:
    """
    Presenter para operaciones de Conversacion y Mensaje.

    Transforma entidades de dominio a schemas HTTP para la capa de presentación.
    """

    # ── Conversacion ───────────────────────────────────────────────────────────

    @staticmethod
    def present_conversacion(conv: Conversacion) -> ConversacionOut:
        """
        Construye un ConversacionOut desde una entidad Conversacion.

        Args:
            conv: Entidad Conversacion.

        Returns:
            ConversacionOut listo para respuesta HTTP.
        """
        estado = (
            EstadoConversacion.CERRADA.value
            if conv.fecha_cierre is not None
            else EstadoConversacion.ABIERTA.value
        )
        return ConversacionOut(
            id=conv.id,
            titulo=conv.titulo,
            creada_por_id=conv.creada_por_id,
            fecha_inicio=conv.fecha_inicio,
            fecha_cierre=conv.fecha_cierre,
            cerrado_por_id=conv.cerrado_por_id if hasattr(conv, "cerrado_por_id") else None,
            estado=estado,
        )

    @staticmethod
    def present_conversacion_detail(
        conv: Conversacion,
        mensajes: list[Mensaje],
    ) -> ConversacionDetailOut:
        """
        Construye un ConversacionDetailOut con mensajes cargados.

        Args:
            conv: Entidad Conversacion.
            mensajes: Lista de entidades Mensaje (prefetched).

        Returns:
            ConversacionDetailOut listo para respuesta HTTP.
        """
        estado = (
            EstadoConversacion.CERRADA.value
            if conv.fecha_cierre is not None
            else EstadoConversacion.ABIERTA.value
        )
        return ConversacionDetailOut(
            id=conv.id,
            titulo=conv.titulo,
            creada_por_id=conv.creada_por_id,
            fecha_inicio=conv.fecha_inicio,
            fecha_cierre=conv.fecha_cierre,
            cerrado_por_id=conv.cerrado_por_id if hasattr(conv, "cerrado_por_id") else None,
            estado=estado,
            mensajes=[
                ConversacionPresenter.present_mensaje(msg) for msg in mensajes
            ],
        )

    # ── Mensaje ───────────────────────────────────────────────────────────────

    @staticmethod
    def present_mensaje(msg: Mensaje) -> MensajeOut:
        """
        Construye un MensajeOut desde una entidad Mensaje.

        Args:
            msg: Entidad Mensaje (con archivos_adjuntos y menciones prefetched si están).

        Returns:
            MensajeOut listo para respuesta HTTP.
        """
        return MensajeOut(
            id=msg.id,
            conversacion_id=msg.conversacion_id,
            autor_usuario_id=msg.autor_usuario_id,
            contenido=msg.contenido,
            tipo=msg.tipo,
            fecha_envio=msg.fecha_envio,
            mensaje_padre_id=msg.mensaje_padre_id,
            editado_at=msg.editado_at,
            eliminado_at=msg.eliminado_at,
            eliminado_por_id=msg.eliminado_por_id if hasattr(msg, "eliminado_por_id") else None,
            archivos_adjuntos=[
                ConversacionPresenter.present_adjunto(adj)
                for adj in (msg.archivos_adjuntos.all() if hasattr(msg, "archivos_adjuntos") else [])
            ],
            menciones=[
                ConversacionPresenter.present_mencion(men)
                for men in (msg.menciones.all() if hasattr(msg, "menciones") else [])
            ],
        )

    @staticmethod
    def present_adjunto(adj) -> ArchivoAdjuntoOut:
        """Construye un ArchivoAdjuntoOut desde una entidad MensajeArchivoAdjunto.

        NOTE: adj.archivo.name puede ser un puntero SAAA (saaa/{app_id}/{archivo_id}/{nombre})
        en lugar de un archivo local. En ese caso, adj.archivo.url devolvería un path
        local inexistente. Se usa resolve_public_url() para distinguir ambos casos
        y retornar la URL correcta.
        """
        archivo_url = resolve_public_url(
            adj.archivo.name if adj.archivo else None,
            adj.archivo if adj.archivo else None,
        )
        return ArchivoAdjuntoOut(
            id=adj.id,
            nombre_original=adj.nombre_original,
            mime_type=adj.mime_type,
            tamano_bytes=adj.tamano_bytes,
            archivo_url=archivo_url,
            descripcion=adj.descripcion if hasattr(adj, "descripcion") else None,
        )

    @staticmethod
    def present_mencion(men) -> MencionOut:
        """Construye un MencionOut desde una entidad MensajeMencion."""
        return MencionOut(
            id=men.id,
            usuario_id=men.usuario_id,
        )
