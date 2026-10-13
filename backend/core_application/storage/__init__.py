"""
core_application.storage — shared storage abstractions for the CIP project.

This package provides:
- pointer.py: Generic SAAA pointer helpers (parse, build, detect).
  A SAAA pointer is a reference to a remote file in the SAAA system,
  NOT a local file. Format: saaa/{app_id}/{archivo_id}/{nombre_original}
- resolvers.py: Shared URL resolution helpers for FileField.name values,
  distinguishing SAAA remote pointers from local file paths.
"""
from core_application.storage.pointer import (
    PREFIX,
    SaaaPointer,
    is_saaa_pointer,
    parse_saaa_pointer,
    build_saaa_pointer,
)
from core_application.storage.resolvers import resolve_public_url

__all__ = [
    "PREFIX",
    "SaaaPointer",
    "is_saaa_pointer",
    "parse_saaa_pointer",
    "build_saaa_pointer",
    "resolve_public_url",
]
