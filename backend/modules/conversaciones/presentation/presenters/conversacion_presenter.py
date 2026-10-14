"""
ConversacionPresenter — transforma resultados del dominio a esquemas HTTP.

Responsabilidad: construir los schemas HTTP (Out) desde las entidades
de dominio o resultados del servicio. Mantiene el controller delgado.
"""

import uuid
from datetime import datetime
from typing import Optional

from django.conf import settings

from core_application.storage.resolvers import resolve_storage_url
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
from modules.tramites.presentation.presenters.archivo_presenter import map_archivo_to_out


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
        """
        Construye un ArchivoAdjuntoOut desde una entidad MensajeArchivoAdjunto.

        Wrapper `id` is the row id; `archivo.id` is the central Archivo id.
        No redundant archivo_id field — use archivo.id instead.
        Uses map_archivo_to_out() for the canonical nested representation.
        Uses resolve_storage_url() for the legacy archivo_url field.
        """
        if adj.archivo:
            archivo_out = map_archivo_to_out(adj.archivo)
            archivo_url = resolve_storage_url(
                storage_backend=adj.archivo.storage_backend,
                storage_reference=adj.archivo.storage_reference,
            )
            nombre_original = adj.archivo.nombre_original or ""
            mime_type = adj.archivo.mime_type
            tamano_bytes = adj.archivo.tamano_bytes
        else:
            archivo_out = None
            archivo_url = ""
            nombre_original = ""
            mime_type = None
            tamano_bytes = None
        return ArchivoAdjuntoOut(
            id=adj.id,
            nombre_original=nombre_original,
            mime_type=mime_type,
            tamano_bytes=tamano_bytes,
            archivo_url=archivo_url,
            descripcion=adj.descripcion if hasattr(adj, "descripcion") else None,
            archivo=archivo_out,
        )

    @staticmethod
    def present_mencion(men) -> MencionOut:
        """Construye un MencionOut desde una entidad MensajeMencion."""
        return MencionOut(
            id=men.id,
            usuario_id=men.usuario_id,
        )
