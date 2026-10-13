"""
Tests para resolve_public_url() en core_application.storage.resolvers.

Valida:
- SAAA pointer (saaa/{app_id}/{archivo_id}/{nombre}) -> proxy URL
- SAAA pointer with FILE_PROXY_URL absolute override -> absolute URL
- Local file path -> local .url
- MEDIA_URL no se rompe para archivos locales
- Absolute HTTP URL -> unchanged
- Empty/None -> empty string
"""
import pytest
from unittest.mock import patch

from django.test import override_settings

from core_application.storage.resolvers import resolve_public_url, _get_proxy_base


class TestResolvePublicUrlSaaaPointer:
    """Tests para SAAA remote pointer resolution."""

    @override_settings(FILE_PROXY_URL="/api/archivo/public/")
    def test_returns_proxy_url_for_saaa_pointer(self):
        """
        GIVEN: a FileField.name that is a SAAA pointer
        WHEN:  resolve_public_url is called
        THEN:  it returns /api/archivo/public/{archivo_id}
        """
        name = "saaa/semana-ingenieria-2026/abc12345/documento.pdf"

        result = resolve_public_url(name, None)

        assert result == "/api/archivo/public/abc12345"

    @override_settings(FILE_PROXY_URL="/api/archivo/public/")
    def test_returns_proxy_url_for_saaa_pointer_with_uuid_archivo_id(self):
        """
        GIVEN: a SAAA pointer with a UUID-like archivo_id
        WHEN:  resolve_public_url is called
        THEN:  the full archivo_id is preserved in the proxy URL
        """
        name = "saaa/semana-ingenieria-2026/4ab48d91-6ff8-48eb-9c6b-3cc9619c31b9/acta.pdf"

        result = resolve_public_url(name, None)

        assert result == "/api/archivo/public/4ab48d91-6ff8-48eb-9c6b-3cc9619c31b9"

    @override_settings(FILE_PROXY_URL="/api/archivo/public/")
    def test_returns_proxy_url_ignores_archivo_url_attr_for_saaa(self):
        """
        GIVEN: a SAAA pointer (archivo_url_attr would return broken local path)
        WHEN:  resolve_public_url is called with archivo_url_attr
        THEN:  the archivo_url_attr is NOT used; proxy URL is returned
        """
        name = "saaa/app-id/uuid-archivo/report.pdf"

        # Simulate a FileField with .url that would return broken path
        class FakeArchivo:
            @property
            def url(self):
                return "/media/saaa/app-id/uuid-archivo/report.pdf"  # broken for SAAA

        result = resolve_public_url(name, FakeArchivo())

        assert result == "/api/archivo/public/uuid-archivo"
        # The FakeArchivo.url property was NOT called (would have returned wrong URL)


class TestResolvePublicUrlLocalFile:
    """Tests para local file resolution."""

    def test_returns_local_url_for_local_path(self):
        """
        GIVEN: a local file path (not a SAAA pointer)
        WHEN:  resolve_public_url is called with archivo_url_attr
        THEN:  it returns the local .url property
        """
        name = "tramites/expedientes/documento.pdf"

        class FakeArchivo:
            @property
            def url(self):
                return "/media/tramites/expedientes/documento.pdf"

        result = resolve_public_url(name, FakeArchivo())

        assert result == "/media/tramites/expedientes/documento.pdf"

    def test_returns_empty_string_when_no_archivo_url_attr_for_local_path(self):
        """
        GIVEN: a local file path but archivo_url_attr is None
        WHEN:  resolve_public_url is called
        THEN:  it returns empty string (no url accessor available)
        """
        name = "tramites/expedientes/documento.pdf"

        result = resolve_public_url(name, None)

        assert result == ""


class TestResolvePublicUrlEdgeCases:
    """Tests para edge cases."""

    def test_returns_empty_string_for_none(self):
        assert resolve_public_url(None, None) == ""

    def test_returns_empty_string_for_empty_string(self):
        assert resolve_public_url("", None) == ""

    def test_returns_absolute_url_unchanged(self):
        """
        GIVEN: an absolute HTTP(S) URL string
        WHEN:  resolve_public_url is called
        THEN:  it returns the URL unchanged
        """
        url = "https://cdn.example.com/files/document.pdf"
        result = resolve_public_url(url, None)
        assert result == url

    def test_returns_http_url_unchanged(self):
        url = "http://internal.file.server/doc.pdf"
        result = resolve_public_url(url, None)
        assert result == url


class TestResolvePublicUrlFileProxyUrlConfig:
    """Tests para FILE_PROXY_URL configuration override."""

    @override_settings(FILE_PROXY_URL="/api/archivo/public/")
    def test_default_proxy_url_is_relative(self):
        """
        GIVEN: default FILE_PROXY_URL (/api/archivo/public/)
        WHEN:  resolve_public_url is called with a SAAA pointer
        THEN:  it returns a relative URL /api/archivo/public/{archivo_id}
        """
        name = "saaa/semana-ingenieria-2026/abc12345/documento.pdf"

        result = resolve_public_url(name, None)

        assert result == "/api/archivo/public/abc12345"

    def test_absolute_proxy_url_override(self):
        """
        GIVEN: FILE_PROXY_URL set to absolute URL (http://localhost:12001/api/archivo/public/)
        WHEN:  resolve_public_url is called with a SAAA pointer
        THEN:  it returns an absolute URL
        """
        name = "saaa/semana-ingenieria-2026/abc12345/documento.pdf"

        with patch("core_application.storage.resolvers.settings") as mock_settings:
            mock_settings.FILE_PROXY_URL = "http://localhost:12001/api/archivo/public/"

            result = resolve_public_url(name, None)

        assert result == "http://localhost:12001/api/archivo/public/abc12345"

    def test_absolute_proxy_url_https(self):
        """
        GIVEN: FILE_PROXY_URL set to https absolute URL
        WHEN:  resolve_public_url is called with a SAAA pointer
        THEN:  it returns the https absolute URL
        """
        name = "saaa/prod-app/xyz789/documento.pdf"

        with patch("core_application.storage.resolvers.settings") as mock_settings:
            mock_settings.FILE_PROXY_URL = "https://saaa.example.com/api/archivo/public/"

            result = resolve_public_url(name, None)

        assert result == "https://saaa.example.com/api/archivo/public/xyz789"

    def test_proxy_url_no_trailing_slash(self):
        """
        GIVEN: FILE_PROXY_URL without trailing slash
        WHEN:  resolve_public_url is called with a SAAA pointer
        THEN:  the archivo_id is appended correctly (no double-slash)
        """
        name = "saaa/app/archivo-id/acta.pdf"

        with patch("core_application.storage.resolvers.settings") as mock_settings:
            mock_settings.FILE_PROXY_URL = "http://localhost:12001/api/archivo/public"  # no trailing slash

            result = resolve_public_url(name, None)

        assert result == "http://localhost:12001/api/archivo/public/archivo-id"

    def test_local_media_url_not_affected_by_file_proxy_url(self):
        """
        GIVEN: FILE_PROXY_URL set to an absolute override
        WHEN:  resolve_public_url is called with a local file path
        THEN:  the local .url is returned (not the proxy URL)
               MEDIA_URL is not mixed with SAAA proxy
        """
        name = "tramites/expedientes/documento.pdf"

        class FakeArchivo:
            @property
            def url(self):
                return "/media/tramites/expedientes/documento.pdf"

        with patch("core_application.storage.resolvers.settings") as mock_settings:
            mock_settings.FILE_PROXY_URL = "http://localhost:12001/api/archivo/public/"

            result = resolve_public_url(name, FakeArchivo())

        # Local file resolution is independent of FILE_PROXY_URL
        assert result == "/media/tramites/expedientes/documento.pdf"

    def test_get_proxy_base_default(self):
        """
        GIVEN: no FILE_PROXY_URL setting
        WHEN:  _get_proxy_base is called
        THEN:  it returns the default /api/archivo/public/
        """
        with patch("core_application.storage.resolvers.settings") as mock_settings:
            mock_settings.FILE_PROXY_URL = "/api/archivo/public/"

            result = _get_proxy_base()

        assert result == "/api/archivo/public/"

    def test_get_proxy_base_absolute_url(self):
        """
        GIVEN: FILE_PROXY_URL set to absolute URL
        WHEN:  _get_proxy_base is called
        THEN:  it returns the absolute URL unchanged
        """
        with patch("core_application.storage.resolvers.settings") as mock_settings:
            mock_settings.FILE_PROXY_URL = "http://localhost:12001/api/archivo/public/"

            result = _get_proxy_base()

        assert result == "http://localhost:12001/api/archivo/public/"
