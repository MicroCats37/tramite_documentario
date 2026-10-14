"""
Conversacion HTTP schemas — Ninja Schema for API request/response.

These are the HTTP-level DTOs, distinct from domain/schemas/ which are
internal service DTOs.
"""

import uuid
from datetime import datetime
from typing import Optional

from django.core.files.uploadedfile import UploadedFile
from ninja import Field

from core.types import BaseSchema
from modules.tramites.presentation.schemas.archivo_out import ArchivoOut


class ArchivoAdjuntoOut(BaseSchema):
    """
    Archivo adjunto en respuesta de mensaje.

    Wrapper `id` is the contextual row id (MensajeArchivoAdjunto.id).
    Nested `archivo` carries the central Archivo id via `archivo.id`.
    Legacy flat fields (nombre_original, archivo_url, mime_type, tamano_bytes)
    preserved for backward compat — consumers should prefer `archivo.*`.
    """

    # Contextual row id — NOT a duplicate of archivo.id
    id: uuid.UUID
    # Legacy flat fields — preserved for backward compat
    nombre_original: str
    mime_type: Optional[str]
    tamano_bytes: Optional[int]
    archivo_url: Optional[str] = Field(
        default=None,
        description="URL del archivo si está presente en el FileField.",
    )
    descripcion: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Descripción opcional del archivo adjunto.",
    )
    # Nested canonical representation — archivo.id is the central Archivo id
    archivo: Optional[ArchivoOut] = Field(
        default=None,
        description="Canonical nested Archivo representation. Use archivo.id as the central Archivo id.",
    )


class MencionOut(BaseSchema):
    """Mención de usuario en mensaje."""

    id: uuid.UUID
    usuario_id: uuid.UUID


class ArchivoAdjuntoCreateIn(BaseSchema):
    """
    Attachment data for creating a mensaje attachment.

    When sent via dual-payload FormData, the archivo field carries the real
    UploadedFile which is hydrated via parse_form_json token replacement.
    For text-only messages, only metadata is provided.
    """

    nombre_original: str = Field(..., max_length=255, description="Nombre original del archivo")
    mime_type: Optional[str] = Field(None, max_length=100, description="Tipo MIME")
    tamano_bytes: Optional[int] = Field(None, description="Tamaño en bytes")
    archivo: Optional[UploadedFile] = Field(
        default=None,
        description="Archivo upload (token en FormData). Opcional para mensajes de solo texto.",
    )
    descripcion: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Descripción opcional del archivo adjunto.",
    )

    model_config = {"arbitrary_types_allowed": True}


class MencionCreateIn(BaseSchema):
    """Mention data for creating a mensaje mention."""

    usuario_id: uuid.UUID = Field(..., description="UUID del usuario mencionado")

    model_config = {"arbitrary_types_allowed": True}


class MensajeOut(BaseSchema):
    """Un mensaje en una conversación."""

    id: uuid.UUID
    conversacion_id: uuid.UUID
    autor_usuario_id: Optional[uuid.UUID]
    contenido: Optional[str]
    tipo: str
    fecha_envio: datetime
    mensaje_padre_id: Optional[uuid.UUID]
    editado_at: Optional[datetime]
    eliminado_at: Optional[datetime]
    eliminado_por_id: Optional[uuid.UUID]
    archivos_adjuntos: list[ArchivoAdjuntoOut]
    menciones: list[MencionOut]


class MensajeCreateIn(BaseSchema):
    """Request body for posting a new mensaje."""

    contenido: Optional[str] = Field(
        None,
        description="Texto del mensaje. Obligatorio si no hay archivos_adjuntos.",
    )
    archivos_adjuntos: list[ArchivoAdjuntoCreateIn] = Field(
        default_factory=list,
        description="Lista de archivos adjuntos (metadata).",
    )
    menciones: list[MencionCreateIn] = Field(
        default_factory=list,
        description="Lista de menciones de usuarios.",
    )
    mensaje_padre_id: Optional[uuid.UUID] = Field(
        None,
        description="UUID del mensaje padre (reply). Opcional.",
    )

    model_config = {"arbitrary_types_allowed": True}


class ConversacionCreateIn(BaseSchema):
    """Request body for creating a new conversacion."""

    titulo: Optional[str] = Field(
        None,
        max_length=255,
        description="Título opcional de la conversación.",
    )
    solicitud_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de la Solicitud a vincular (opcional).",
    )

    model_config = {"arbitrary_types_allowed": True}


class ConversacionOut(BaseSchema):
    """Conversacion sin sus mensajes (para listados)."""

    id: uuid.UUID
    titulo: Optional[str]
    creada_por_id: uuid.UUID
    fecha_inicio: datetime
    fecha_cierre: Optional[datetime]
    cerrado_por_id: Optional[uuid.UUID]
    estado: str


class ConversacionDetailOut(BaseSchema):
    """Detalle completo de una conversación con sus mensajes."""

    id: uuid.UUID
    titulo: Optional[str]
    creada_por_id: uuid.UUID
    fecha_inicio: datetime
    fecha_cierre: Optional[datetime]
    cerrado_por_id: Optional[uuid.UUID]
    estado: str
    mensajes: list[MensajeOut]


class ConversacionCerrarIn(BaseSchema):
    """Request body for closing a conversacion."""

    model_config = {"arbitrary_types_allowed": True}
