"""
Shared fixtures index for conversaciones tests.

Phase 1: only model factories (factories.py) are defined.
Phase 2+ will add real fixtures and integration/e2e tests.
"""
from modules.conversaciones.tests.factories import (
    make_conversacion_payload,
    make_mensaje_payload,
    make_mensaje_archivo_adjunto_payload,
    make_mensaje_mencion_payload,
    make_solicitud_conversacion_payload,
)
