"""
Integration tests — re-export fixtures from root conftest.
"""

from modules.conversaciones.tests.conftest import (
    make_conversacion_payload,
    make_mensaje_payload,
    make_mensaje_archivo_adjunto_payload,
    make_mensaje_mencion_payload,
    make_solicitud_conversacion_payload,
)
