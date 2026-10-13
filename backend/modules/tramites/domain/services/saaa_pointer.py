"""
SAAA Pointer Helpers — utilities para parsear y construir punteros SAAA en FileField.name.

Formato de puntero: saaa/{app_id}/{archivo_id}/{nombre_original}
Ejemplo: saaa/semana-ingenieria-2026/abc12345/documento.pdf

Estas funciones permiten:
- is_saaa_pointer(): detectar si un nombre es un puntero SAAA
- parse_saaa_pointer(): extraer componentes del puntero
- build_saaa_pointer(): construir un puntero desde componentes

NOTA: Las implementaciones reales viven ahora en core_application.storage.pointer.
Este módulo mantiene backward compatibility re-exportando desde ahí.
"""
# Re-export from core for backward compat — existing imports in other modules
# continue to work without changes
from core_application.storage.pointer import (
    PREFIX as PREFIX,
    SaaaPointer,
    is_saaa_pointer,
    parse_saaa_pointer,
    build_saaa_pointer,
)

__all__ = [
    "PREFIX",
    "SaaaPointer",
    "is_saaa_pointer",
    "parse_saaa_pointer",
    "build_saaa_pointer",
]
