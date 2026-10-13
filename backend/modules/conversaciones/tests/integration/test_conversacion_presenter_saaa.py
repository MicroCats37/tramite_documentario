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
        GIVEN: a MensajeArchivoAdjunto whose archivo.name is a SAAA pointer
        WHEN:  present_adjunto is called
        THEN:  it returns /api/archivo/public/{archivo_id}
        """
        class FakeArchivo:
            name = "saaa/semana-ingenieria-2026/abc12345/documento.pdf"

            @property
            def url(self):
                # This would be the broken local path for a SAAA pointer
                return "/media/saaa/semana-ingenieria-2026/abc12345/documento.pdf"

        class FakeAdjunto:
            id = uuid.uuid4()
            archivo = FakeArchivo()
            nombre_original = "documento.pdf"
            mime_type = "application/pdf"
            tamano_bytes = 2048
            descripcion = None

        out = ConversacionPresenter.present_adjunto(FakeAdjunto())

        assert out.archivo_url == "/api/archivo/public/abc12345"
        assert out.nombre_original == "documento.pdf"

    @override_settings(FILE_PROXY_URL="/api/archivo/public/")
    def test_returns_proxy_url_for_saaa_pointer_with_uuid(self):
        """
        GIVEN: a MensajeArchivoAdjunto with a UUID-based SAAA pointer
        WHEN:  present_adjunto is called
        THEN:  the full archivo_id is preserved in the proxy URL
        """
        class FakeArchivo:
            name = "saaa/semana-ingenieria-2026/4ab48d91-6ff8-48eb-9c6b-3cc9619c31b9/acta.pdf"

            @property
            def url(self):
                return "/media/saaa/semana-ingenieria-2026/4ab48d91-6ff8-48eb-9c6b-3cc9619c31b9/acta.pdf"

        class FakeAdjunto:
            id = uuid.uuid4()
            archivo = FakeArchivo()
            nombre_original = "acta.pdf"
            mime_type = "application/pdf"
            tamano_bytes = 5120
            descripcion = None

        out = ConversacionPresenter.present_adjunto(FakeAdjunto())

        assert out.archivo_url == "/api/archivo/public/4ab48d91-6ff8-48eb-9c6b-3cc9619c31b9"

    def test_returns_local_url_for_local_file(self):
        """
        GIVEN: a MensajeArchivoAdjunto with a local file (not a SAAA pointer)
        WHEN:  present_adjunto is called
        THEN:  it returns the local .url property
        """
        class FakeArchivo:
            name = "conversaciones/mensajes/attachment.pdf"

            @property
            def url(self):
                return "/media/conversaciones/mensajes/attachment.pdf"

        class FakeAdjunto:
            id = uuid.uuid4()
            archivo = FakeArchivo()
            nombre_original = "attachment.pdf"
            mime_type = "application/pdf"
            tamano_bytes = 1024
            descripcion = None

        out = ConversacionPresenter.present_adjunto(FakeAdjunto())

        assert out.archivo_url == "/media/conversaciones/mensajes/attachment.pdf"
        assert out.nombre_original == "attachment.pdf"

    def test_returns_empty_string_when_archivo_is_none(self):
        """
        GIVEN: a MensajeArchivoAdjunto with archivo=None
        WHEN:  present_adjunto is called
        THEN:  it returns an empty string for archivo_url
        """
        class FakeAdjunto:
            id = uuid.uuid4()
            archivo = None
            nombre_original = "orphaned.pdf"
            mime_type = "application/pdf"
            tamano_bytes = 0
            descripcion = None

        out = ConversacionPresenter.present_adjunto(FakeAdjunto())

        assert out.archivo_url == ""
