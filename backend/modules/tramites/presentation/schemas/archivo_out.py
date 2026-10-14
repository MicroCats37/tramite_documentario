"""
ArchivoOut — canonical nested file representation.

This schema is the canonical nested representation of an Archivo.
It is reused across all output contexts (Expediente, Conversacion, SolicitudRespuesta)
during Phase 1 additive standardization.

Legacy flat fields are preserved for backward compatibility;
new consumers should prefer the nested `archivo` field.
"""
import uuid
from typing import Optional

from ninja import Field

from core.types import BaseSchema


class ArchivoOut(BaseSchema):
    """
    Canonical nested file representation.

    Fields:
        id: Archivo UUID identifier.
        nombre_original: Original filename as uploaded.
        mime_type: MIME type if known.
        tamano_bytes: File size in bytes if known.
        url: Resolved public URL via resolve_storage_url(). Nullable because
            some storage backends may not produce a URL.
    """

    id: uuid.UUID
    nombre_original: str
    mime_type: Optional[str] = None
    tamano_bytes: Optional[int] = None
    url: Optional[str] = None
