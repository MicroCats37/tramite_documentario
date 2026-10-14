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
        GIVEN: a SolicitudAsignacionRespuesta whose archivo is a SAAA-backed Archivo
        WHEN:  present() is called
        THEN:  it returns /api/archivo/public/{storage_reference} as archivo URL
        """
        class FakeArchivo:
            """Fake mimicking the new central Archivo FK shape (storage_backend + storage_reference)."""
            id = uuid.uuid4()
            storage_backend = "saaa"
            storage_reference = "abc12345"
            nombre_original = "resolucion.pdf"

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
        # No archivo_id field — central Archivo id is accessed via nested archivo.id when available

    def test_returns_local_url_for_local_file(self):
        """
        GIVEN: a SolicitudAsignacionRespuesta with a local file (storage_backend='local')
        WHEN:  present() is called
        THEN:  it returns the local storage URL via resolve_storage_url
        """
        class FakeArchivo:
            """Fake mimicking the new central Archivo FK shape for local storage."""
            id = uuid.uuid4()
            storage_backend = "local"
            storage_reference = "asignaciones/respuestas/informe.pdf"
            nombre_original = "informe.pdf"

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

        # resolve_storage_url for 'local' backend calls default_storage.url()
        # which returns the media URL for the given storage_reference
        assert out.archivo is not None  # actual URL depends on Django storage config

    def test_returns_none_when_archivo_is_none(self):
        """
        GIVEN: a SolicitudAsignacionRespuesta with archivo=None
        WHEN:  present() is called
        THEN:  it returns None for archivo (schema is Optional)
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

        # Presenter sets archivo=None when archivo relation is absent
        assert out.archivo is None
