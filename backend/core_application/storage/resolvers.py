"""
Shared URL resolution helpers for FileField.name values.

This module provides a single entry point for resolving the public URL of any
file referenced in a FileField — whether the file is stored locally or is a
SAAA remote pointer.

IMPORTANT — SAAA Remote Pointers:
When a FileField.name starts with "saaa/", the actual file bytes are stored
in the SAAA remote service, NOT on the local filesystem. Django's FileSystemStorage
will NOT find a local file at that path. ALWAYS use resolve_public_url() to
get the correct URL instead of calling .url directly on the FileField.

Resolution strategy:
- SAAA pointer (saaa/{app_id}/{archivo_id}/{nombre_original})
    -> Returns {FILE_PROXY_URL}{archivo_id} (the Django proxy endpoint or absolute URL)
    -> If FILE_PROXY_URL is absolute (http:// or https://), returns absolute URL
    -> If FILE_PROXY_URL is relative (e.g., /api/archivo/public/), returns relative URL
- Local file path (e.g., "tramites/expedientes/documento.pdf")
    -> Returns archivo.url (the local media URL via Django's storage backend)
- String URL (http:// or https://)
    -> Returns the string as-is (already an absolute URL)
- Empty/None
    -> Returns an empty string

Configuration:
- FILE_PROXY_URL: Set via FILE_PROXY_URL env var.
  Default: "/api/archivo/public/" (relative, works for any deployment)
  Example absolute: "http://localhost:12001/api/archivo/public/"
  NOTE: Do NOT mix with MEDIA_URL — this is ONLY for SAAA proxy endpoints.
"""
from django.conf import settings

from core_application.storage.pointer import is_saaa_pointer, parse_saaa_pointer


def _get_proxy_base() -> str:
    """
    Returns the configured SAAA proxy base URL from settings.

    Defaults to /api/archivo/public/ if not configured.
    Handles both relative (e.g., /api/archivo/public/) and absolute
    (e.g., http://localhost:12001/api/archivo/public/) values.
    """
    return getattr(settings, "FILE_PROXY_URL", "/api/archivo/public/")


def resolve_public_url(archivo_field_name: str | None, archivo_url_attr=None) -> str:
    """
    Resolves the public URL for any file field value.

    Distinguishes between SAAA remote pointers and local files, returning
    the appropriate URL in each case.

    Args:
        archivo_field_name: The value of FileField.name (e.g., archivo.name)
            This is what gets stored in the database and determines the storage type.
        archivo_url_attr: The FileField's .url property accessor.
            Only used when the file is a local file (not a SAAA pointer).
            Pass the FileField object itself, e.g. archivo.url

    Returns:
        - SAAA pointer: /api/archivo/public/{archivo_id}
        - Local file: archivo.url (local media URL)
        - String URL: the string unchanged
        - Empty/None: empty string

    Example:
        # In a presenter:
        url = resolve_public_url(archivo.name, archivo)

        # archivo.name = "saaa/semana-ingenieria-2026/abc12345/doc.pdf"
        # Returns: "/api/archivo/public/abc12345"

        # archivo.name = "tramites/expedientes/doc.pdf"
        # Returns: "/media/tramites/expedientes/doc.pdf" (or absolute URL)
    """
    if not archivo_field_name:
        return ""

    # If it looks like an already-resolved absolute URL, return as-is
    if archivo_field_name.startswith(("http://", "https://")):
        return archivo_field_name

    # SAAA remote pointer — return the proxy endpoint URL
    if is_saaa_pointer(archivo_field_name):
        pointer = parse_saaa_pointer(archivo_field_name)
        if not pointer:
            return ""
        # The proxy endpoint expects only the archivo_id to look up the file in SAAA
        proxy_base = _get_proxy_base()
        # Strip any trailing slash from proxy_base, then append archivo_id
        # This handles both relative (/api/archivo/public/) and absolute
        # (http://localhost:12001/api/archivo/public/) FILE_PROXY_URL values
        base = proxy_base.rstrip("/")
        return f"{base}/{pointer.archivo_id}"

    # Local file — use the FileField's .url property
    if archivo_url_attr is not None:
        return getattr(archivo_url_attr, "url", "")

    # Fallback: empty string for unknown/invalid values
    return ""
