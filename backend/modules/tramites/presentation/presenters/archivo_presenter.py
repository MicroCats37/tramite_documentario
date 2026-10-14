"""
ArchivoPresenter — shared presenter helper for mapping Archivo model to ArchivoOut.

Provides a reusable mapper that resolves storage URLs and builds the canonical
ArchivoOut nested representation. Used by all output contexts (Expediente,
Conversacion, SolicitudRespuesta) to avoid duplicating mapping logic.
"""
from core_application.storage.resolvers import resolve_storage_url
from modules.tramites.domain.models.archivo import Archivo
from modules.tramites.presentation.schemas.archivo_out import ArchivoOut


def map_archivo_to_out(archivo: Archivo | None) -> ArchivoOut | None:
    """
    Maps an Archivo model instance to an ArchivoOut schema.

    Args:
        archivo: Archivo model instance, or None.

    Returns:
        ArchivoOut if archivo is provided, None otherwise.
    """
    if archivo is None:
        return None

    url = resolve_storage_url(
        storage_backend=archivo.storage_backend,
        storage_reference=archivo.storage_reference,
    )

    return ArchivoOut(
        id=archivo.id,
        nombre_original=archivo.nombre_original or "",
        mime_type=archivo.mime_type,
        tamano_bytes=archivo.tamano_bytes,
        url=url or None,
    )
