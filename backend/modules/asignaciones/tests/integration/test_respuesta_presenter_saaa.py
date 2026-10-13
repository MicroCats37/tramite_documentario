"""
Tests para RespuestaPresenter.present() con punteros SAAA.

Valida:
- present() returns proxy URL for SAAA pointer (saaa/{app_id}/{archivo_id}/...)
- present() returns local .url for local file
"""
import uuid

import pytest
from django.test import override_settings

from modules.asignaciones.presentation.presenters.respuesta_presenter import (
    RespuestaPresenter,
)


class TestRespuestaPresenterSaaaPointer:
    """Tests para RespuestaPresenter con SAAA pointers."""

    @override_settings(FILE_PROXY_URL="/api/archivo/public/")
    def test_returns_proxy_url_for_saaa_pointer(self):
        """
        GIVEN: a SolicitudAsignacionRespuesta whose archivo.name is a SAAA pointer
        WHEN:  present() is called
        THEN:  it returns /api/archivo/public/{archivo_id}
        """
        class FakeArchivo:
            name = "saaa/semana-ingenieria-2026/abc12345/resolucion.pdf"

            @property
            def url(self):
                # Broken path for SAAA pointer
                return "/media/saaa/semana-ingenieria-2026/abc12345/resolucion.pdf"

        class FakeRespuesta:
            id = uuid.uuid4()
            periodo_id = uuid.uuid4()
            tipo_respuesta = "INFORME"
            contenido = "Informe de respuesta"
            archivo = FakeArchivo()
            estado = "BORRADOR"
            version = 1
            observacion = None
            fecha_emision = None
            emitido_por_id = None
            created_at = "2026-09-18T00:00:00Z"
            updated_at = "2026-09-18T00:00:00Z"

        out = RespuestaPresenter.present(FakeRespuesta())

        assert out.archivo == "/api/archivo/public/abc12345"

    def test_returns_local_url_for_local_file(self):
        """
        GIVEN: a SolicitudAsignacionRespuesta with a local file (not a SAAA pointer)
        WHEN:  present() is called
        THEN:  it returns the local .url property
        """
        class FakeArchivo:
            name = "asignaciones/respuestas/informe.pdf"

            @property
            def url(self):
                return "/media/asignaciones/respuestas/informe.pdf"

        class FakeRespuesta:
            id = uuid.uuid4()
            periodo_id = uuid.uuid4()
            tipo_respuesta = "INFORME"
            contenido = "Informe"
            archivo = FakeArchivo()
            estado = "BORRADOR"
            version = 1
            observacion = None
            fecha_emision = None
            emitido_por_id = None
            created_at = "2026-09-18T00:00:00Z"
            updated_at = "2026-09-18T00:00:00Z"

        out = RespuestaPresenter.present(FakeRespuesta())

        assert out.archivo == "/media/asignaciones/respuestas/informe.pdf"

    def test_returns_empty_string_when_archivo_is_none(self):
        """
        GIVEN: a SolicitudAsignacionRespuesta with archivo=None
        WHEN:  present() is called
        THEN:  it returns an empty string (resolve_public_url returns "" for None)
        """
        class FakeRespuesta:
            id = uuid.uuid4()
            periodo_id = uuid.uuid4()
            tipo_respuesta = "OBSERVACION"
            contenido = "Observación sin archivo"
            archivo = None
            estado = "BORRADOR"
            version = 1
            observacion = None
            fecha_emision = None
            emitido_por_id = None
            created_at = "2026-09-18T00:00:00Z"
            updated_at = "2026-09-18T00:00:00Z"

        out = RespuestaPresenter.present(FakeRespuesta())

        # resolve_public_url returns "" for None input, which is valid for Optional[str]
        assert out.archivo == ""
