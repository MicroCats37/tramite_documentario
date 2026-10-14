"""
Tests para ConversacionPresenter.present_adjunto con punteros SAAA.

Valida:
- present_adjunto() returns proxy URL for SAAA pointer (saaa/{app_id}/{archivo_id}/...)
- present_adjunto() returns local .url for local file
- present_adjunto() returns empty string when archivo is None
"""
import uuid

import pytest
from django.test import override_settings

from modules.conversaciones.presentation.presenters.conversacion_presenter import (
    ConversacionPresenter,
)


class TestConversacionPresenterAdjuntoSaaa:
    """Tests para present_adjunto() con SAAA pointers."""

    @override_settings(FILE_PROXY_URL="/api/archivo/public/")
    def test_returns_proxy_url_for_saaa_pointer(self):
        """
        GIVEN: a MensajeArchivoAdjunto whose archivo FK has storage_backend='saaa'
               and storage_reference pointing to a SAAA archivo_id
        WHEN:  present_adjunto is called
        THEN:  it returns /api/archivo/public/{archivo_id}
        """
        class FakeArchivo:
            id = uuid.uuid4()
            storage_backend = "saaa"
            storage_reference = "abc12345"
            nombre_original = "documento.pdf"
            mime_type = "application/pdf"
            tamano_bytes = 2048

        class FakeAdjunto:
            id = uuid.uuid4()
            archivo = FakeArchivo()
            descripcion = None

        out = ConversacionPresenter.present_adjunto(FakeAdjunto())

        assert out.archivo_url == "/api/archivo/public/abc12345"
        assert out.nombre_original == "documento.pdf"
        assert out.mime_type == "application/pdf"
        assert out.tamano_bytes == 2048

    @override_settings(FILE_PROXY_URL="/api/archivo/public/")
    def test_returns_proxy_url_for_saaa_pointer_with_uuid(self):
        """
        GIVEN: a MensajeArchivoAdjunto with a UUID-based SAAA storage_reference
        WHEN:  present_adjunto is called
        THEN:  the full archivo_id is preserved in the proxy URL
        """
        class FakeArchivo:
            id = uuid.uuid4()
            storage_backend = "saaa"
            storage_reference = "4ab48d91-6ff8-48eb-9c6b-3cc9619c31b9"
            nombre_original = "acta.pdf"
            mime_type = "application/pdf"
            tamano_bytes = 5120

        class FakeAdjunto:
            id = uuid.uuid4()
            archivo = FakeArchivo()
            descripcion = None

        out = ConversacionPresenter.present_adjunto(FakeAdjunto())

        assert out.archivo_url == "/api/archivo/public/4ab48d91-6ff8-48eb-9c6b-3cc9619c31b9"
        assert out.nombre_original == "acta.pdf"

    def test_returns_local_url_for_local_file(self):
        """
        GIVEN: a MensajeArchivoAdjunto with a local file (storage_backend='local')
        WHEN:  present_adjunto is called
        THEN:  it returns the local default_storage URL
        """
        class FakeArchivo:
            id = uuid.uuid4()
            storage_backend = "local"
            storage_reference = "conversaciones/mensajes/attachment.pdf"
            nombre_original = "attachment.pdf"
            mime_type = "application/pdf"
            tamano_bytes = 1024

        class FakeAdjunto:
            id = uuid.uuid4()
            archivo = FakeArchivo()
            descripcion = None

        out = ConversacionPresenter.present_adjunto(FakeAdjunto())

        assert out.archivo_url is not None
        assert "attachment.pdf" in out.archivo_url
        assert out.nombre_original == "attachment.pdf"

    def test_returns_empty_string_when_archivo_is_none(self):
        """
        GIVEN: a MensajeArchivoAdjunto with archivo=None
        WHEN:  present_adjunto is called
        THEN:  it returns an empty string for archivo_url and None/empty for metadata
        """
        class FakeAdjunto:
            id = uuid.uuid4()
            archivo = None
            descripcion = None

        out = ConversacionPresenter.present_adjunto(FakeAdjunto())

        assert out.archivo_url == ""
        assert out.nombre_original == ""
        assert out.mime_type is None
        assert out.tamano_bytes is None
