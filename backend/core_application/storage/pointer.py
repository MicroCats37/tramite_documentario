"""
SAAA Pointer Helpers — generic utilities for parsing and building SAAA pointers in FileField.name.

IMPORTANT: A SAAA pointer is a REFERENCE to a remote file stored in the SAAA
service, NOT an actual local file. The pointer format is:

    saaa/{app_id}/{archivo_id}/{nombre_original}

Example: saaa/semana-ingenieria-2026/abc12345/documento.pdf

When a FileField.name starts with "saaa/", it means:
- The actual file bytes are stored in the SAAA remote service
- The local FileField stores only the pointer string as its "name"
- Django's FileSystemStorage will NOT find a local file at that path
- The URL must be resolved via resolve_public_url() in resolvers.py

Pointer format components:
- app_id: The SAAA application ID (e.g., 'semana-ingenieria-2026')
- archivo_id: The file ID assigned by SAAA (UUID or string identifier)
- nombre_original: The original filename when uploaded

These helpers are generic and app-agnostic. They do NOT depend on any
business module (tramites, asignaciones, conversaciones, etc.).
"""
from dataclasses import dataclass


PREFIX = "saaa/"


@dataclass(frozen=True)
class SaaaPointer:
    """
    Parsed SAAA pointer components.

    Attributes:
        app_id: SAAA application ID (e.g., 'semana-ingenieria-2026')
        archivo_id: File ID assigned by SAAA (UUID or string)
        nombre_original: Original filename when uploaded
    """
    app_id: str
    archivo_id: str
    nombre_original: str


def is_saaa_pointer(name: str | None) -> bool:
    """
    Detects whether a FileField.name value is a SAAA remote pointer.

    Args:
        name: The value of a FileField.name attribute

    Returns:
        True if the name is a SAAA pointer (starts with 'saaa/')
    """
    if not name:
        return False
    return name.startswith(PREFIX)


def parse_saaa_pointer(name: str | None) -> SaaaPointer | None:
    """
    Parses a SAAA pointer and returns its components.

    Expected format: saaa/{app_id}/{archivo_id}/{nombre_original}

    Args:
        name: The value of a FileField.name attribute

    Returns:
        SaaaPointer with components, or None if not a valid pointer
    """
    if not name or not name.startswith(PREFIX):
        return None

    rest = name[len(PREFIX):]
    parts = rest.split("/", 3)

    if len(parts) < 3:
        return None

    app_id = parts[0]
    archivo_id = parts[1]
    # The original name may contain "/" characters, so we take part index 2
    nombre_original = parts[2]

    return SaaaPointer(
        app_id=app_id,
        archivo_id=archivo_id,
        nombre_original=nombre_original,
    )


def build_saaa_pointer(app_id: str, archivo_id: str, nombre_original: str) -> str:
    """
    Builds a SAAA pointer string for storage in FileField.name.

    Args:
        app_id: SAAA application ID
        archivo_id: File ID assigned by SAAA
        nombre_original: Original filename

    Returns:
        Pointer string in format saaa/{app_id}/{archivo_id}/{nombre_original}
    """
    return f"{PREFIX}{app_id}/{archivo_id}/{nombre_original}"
