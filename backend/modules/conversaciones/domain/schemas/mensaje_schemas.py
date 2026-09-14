"""
Mensaje schemas — DTOs for mensaje-related operations.
"""

from datetime import datetime, timezone as dt_timezone
from uuid import UUID

from django.core.files.uploadedfile import UploadedFile
from pydantic import BaseModel, Field, model_validator


def _now():
    return datetime.now(dt_timezone.utc)


class MensajeArchivoAdjuntoData(BaseModel):
    """
    Attachment data for creating a MensajeArchivoAdjunto.

    Includes the actual UploadedFile when sent via dual-payload FormData.
    The archivo field is set when real files are uploaded; otherwise only
    metadata is provided (nombre_original, mime_type, tamano_bytes).
    """

    nombre_original: str = Field(max_length=255)
    mime_type: str | None = Field(default=None, max_length=100)
    tamano_bytes: int | None = None
    archivo: UploadedFile | None = Field(default=None)
    subido_por_id: UUID
    fecha_archivo: datetime = Field(default_factory=_now)
    descripcion: str | None = Field(default=None, max_length=500)

    model_config = {"arbitrary_types_allowed": True}


class MensajeMencionData(BaseModel):
    """Mention data for creating a MensajeMencion."""

    usuario_id: UUID

    model_config = {"arbitrary_types_allowed": True}


class MensajeCreateData(BaseModel):
    """Input data for creating a Mensaje."""

    conversacion_id: UUID
    autor_usuario_id: UUID | None = None
    contenido: str | None = None
    tipo: str = Field(default="MENSAJE")
    fecha_envio: datetime = Field(default_factory=_now)
    mensaje_padre_id: UUID | None = None
    archivos_adjuntos: list[MensajeArchivoAdjuntoData] = Field(default_factory=list)
    menciones: list[MensajeMencionData] = Field(default_factory=list)

    @model_validator(mode="after")
    def must_have_content_or_attachments(self) -> "MensajeCreateData":
        if not self.contenido and not self.archivos_adjuntos:
            raise ValueError("Mensaje must have contenido or at least one archivo_adjunto")
        return self

    @model_validator(mode="after")
    def sistema_tiene_autor_nulo(self) -> "MensajeCreateData":
        if self.tipo == "SISTEMA" and self.autor_usuario_id is not None:
            raise ValueError("System messages must have autor_usuario_id=null")
        return self

    @model_validator(mode="after")
    def humano_tiene_autor(self) -> "MensajeCreateData":
        if self.tipo != "SISTEMA" and self.autor_usuario_id is None:
            raise ValueError("Non-system messages must have autor_usuario_id")
        return self

    model_config = {"arbitrary_types_allowed": True}


class MensajeDeleteData(BaseModel):
    """Input data for soft-deleting a Mensaje."""

    eliminado_por_id: UUID = Field(description="UUID of the user deleting the message")

    model_config = {"arbitrary_types_allowed": True}
