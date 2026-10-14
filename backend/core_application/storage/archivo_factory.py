"""
Archivo Factory — helpers to create Archivo instances from storage service return values.

The storage service save() methods return strings:
- SAAA pointer: "saaa/{app_id}/{archivo_id}/{nombre_original}"
- Local path: "path/to/file.pdf"
- HTTP/HTTPS URL: "https://example.com/file.pdf"

This module provides utilities to parse these values and create properly
populated Archivo instances.

Usage:
    from core_application.storage.archivo_factory import create_archivo_from_storage_result

    storage_path = storage_service.save(uploaded_file, nombre_original)
    archivo = create_archivo_from_storage_result(
        storage_path=storage_path,
        nombre_original=nombre_original,
        mime_type=mime_type,
        tamano_bytes=tamano_bytes,
        subido_por_id=user_id,
    )
"""
from core_application.storage.pointer import is_saaa_pointer, parse_saaa_pointer


def create_archivo_from_storage_result(
    storage_path: str,
    nombre_original: str | None = None,
    mime_type: str | None = None,
    tamano_bytes: int | None = None,
    subido_por_id: int | None = None,
    storage_namespace: str | None = None,
) -> "Archivo":
    """
    Create an Archivo instance from a storage service return value.

    Args:
        storage_path: The value returned by AbstractStorageService.save().
            - SAAA pointer string: "saaa/{app_id}/{archivo_id}/{nombre_original}"
            - Local path: "path/to/file.pdf"
            - HTTP/HTTPS URL: "https://example.com/file.pdf"
        nombre_original: Original filename (used for SAAA fallback if not in pointer).
        mime_type: MIME type of the file (optional).
        tamano_bytes: Size of the file in bytes (optional).
        subido_por_id: ID of the user who uploaded the file (optional).
        storage_namespace: Optional namespace for the storage (e.g., app_id for SAAA).

    Returns:
        An unsaved Archivo instance with storage_backend, storage_reference,
        and other fields populated appropriately.

    Note:
        The returned Archivo instance is NOT saved to the database.
        Caller must call .save() after creating it.
    """
    from modules.tramites.domain.models import Archivo

    if is_saaa_pointer(storage_path):
        pointer = parse_saaa_pointer(storage_path)
        if pointer is None:
            # Fallback: treat as local
            return _create_local_archivo(
                storage_path, nombre_original, mime_type, tamano_bytes, subido_por_id
            )
        # SAAA pointer: storage_reference is the archivo_id, namespace is app_id
        return Archivo(
            storage_backend="saaa",
            storage_reference=pointer.archivo_id,
            storage_namespace=pointer.app_id if not storage_namespace else storage_namespace,
            nombre_original=pointer.nombre_original if not nombre_original else nombre_original,
            extension=_extension_from_nombre(pointer.nombre_original),
            mime_type=mime_type,
            tamano_bytes=tamano_bytes,
            subido_por_id=subido_por_id,
        )

    elif storage_path.startswith(("http://", "https://")):
        # External URL
        return Archivo(
            storage_backend="external_url",
            storage_reference=storage_path,
            storage_namespace=storage_namespace,
            nombre_original=nombre_original,
            extension=_extension_from_nombre(nombre_original) if nombre_original else None,
            mime_type=mime_type,
            tamano_bytes=tamano_bytes,
            subido_por_id=subido_por_id,
            administrado=False,  # External URLs are not managed by us
        )

    else:
        # Local path
        return _create_local_archivo(
            storage_path, nombre_original, mime_type, tamano_bytes, subido_por_id, storage_namespace
        )


def _create_local_archivo(
    storage_path: str,
    nombre_original: str | None,
    mime_type: str | None,
    tamano_bytes: int | None,
    subido_por_id: int | None,
    storage_namespace: str | None = None,
):
    """Create an Archivo instance for local storage."""
    from modules.tramites.domain.models import Archivo

    if nombre_original is None:
        nombre_original = storage_path.split("/")[-1]

    return Archivo(
        storage_backend="local",
        storage_reference=storage_path,
        storage_namespace=storage_namespace,
        nombre_original=nombre_original,
        extension=_extension_from_nombre(nombre_original),
        mime_type=mime_type,
        tamano_bytes=tamano_bytes,
        subido_por_id=subido_por_id,
    )


def _extension_from_nombre(nombre: str | None) -> str | None:
    """Extract file extension from filename."""
    if not nombre:
        return None
    parts = nombre.rsplit(".", 1)
    if len(parts) == 2:
        return parts[1].lower()
    return None
