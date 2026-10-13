"""
Integration tests for SAAA Archivo Proxy endpoint.

Tests follow TDD cycle: RED (write failing test) → GREEN (implement) → REFACTOR.

Contract rules enforced:
- No unittest.mock.patch — use FakeSaaaClient injection via fixtures
- Tests use @pytest.mark.django_db for real DB access
- TestAsyncClient from ninja_extra.testing (correct for async controllers)

The proxy endpoint (/api/archivo/public/{saaa_id}) serves files stored in SAAA
by decoding the base64 response and returning binary content.

NOTE: These tests call the controller method directly (bypassing URL routing) to
test the proxy logic in isolation. URL routing is verified via Django check.
"""
import pytest

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model

pytestmark = [pytest.mark.django_db(transaction=True)]


# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def make_proxy_request(db):
    """
    Factory fixture that returns a callable to invoke the proxy endpoint.

    Calls the controller method directly (async → sync wrapper) to test logic
    without depending on URL routing in the test client.
    """
    from modules.tramites.presentation.controllers.saaa_archivo_proxy_controller import (
        SaaaArchivoProxyController,
    )
    from modules.tramites.infrastructure.saaa_client import FakeSaaaClient

    def _call(saaa_id: str, saaa_client: FakeSaaaClient = None) -> tuple:
        """Returns (status_code, content_type, content, headers)."""
        if saaa_client is None:
            saaa_client = FakeSaaaClient.get_instance()

        controller = SaaaArchivoProxyController(saaa_client=saaa_client)

        # Create a fake request object
        class FakeRequest:
            pass

        result = async_to_sync(controller.obtener_archivo_publico)(
            FakeRequest(), saaa_id=saaa_id
        )

        return result

    return _call


@pytest.fixture
def saaa_fake(db):
    """Return the FakeSaaaClient singleton (same instance used by the controller via DI)."""
    from modules.tramites.infrastructure.saaa_client import FakeSaaaClient
    return FakeSaaaClient.get_instance()


# ── Tests ──────────────────────────────────────────────────────────────────────


def test_proxy_returns_200_with_binary_content_for_valid_saaa_id(saaa_fake, make_proxy_request):
    """
    GIVEN: a valid SAAA archivo_id stored in the FakeSaaaClient singleton
    WHEN:  the proxy endpoint is called with that saaa_id
    THEN:  response status is 200
            AND Content-Type is application/pdf (from extension)
            AND Content-Disposition inline
            AND body is the binary file content (not base64)
    """
    contenido = b"%PDF-1.4 fake test content"
    upload_result = saaa_fake.subir_archivo(
        file_content=contenido,
        nombre_original="documento.pdf",
        aplicacion_id="test-app",
        usuario_id="1",
        tipo_archivo_id="1",
    )
    archivo_id = upload_result.id

    response = make_proxy_request(archivo_id, saaa_client=saaa_fake)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.headers.get("content-type", "").startswith("application/pdf")
    assert "inline" in response.headers.get("content-disposition", "")
    # StreamingHttpResponse: content is in streaming_content
    assert b"".join(response.streaming_content) == contenido


def test_proxy_returns_404_for_unknown_saaa_id(saaa_fake, make_proxy_request):
    """
    GIVEN: a SAAA archivo_id that does not exist in SAAA
    WHEN:  the proxy endpoint is called with that unknown saaa_id
    THEN:  response status is 404
    """
    response = make_proxy_request("no-existe-id-xyz", saaa_client=saaa_fake)

    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}"
    )


def test_proxy_returns_correct_content_type_for_jpg(saaa_fake, make_proxy_request):
    """
    GIVEN: a JPG file stored in the fake SAAA client
    WHEN:  the proxy endpoint is called with that saaa_id
    THEN:  Content-Type is image/jpeg
    """
    contenido = b"\xff\xd8\xff\xe0 fake jpg content"
    upload_result = saaa_fake.subir_archivo(
        file_content=contenido,
        nombre_original="foto.jpg",
        aplicacion_id="test-app",
        usuario_id="1",
        tipo_archivo_id="1",
    )

    response = make_proxy_request(upload_result.id, saaa_client=saaa_fake)

    assert response.status_code == 200
    assert "image/jpeg" in response.headers.get("content-type", "")


def test_proxy_returns_correct_content_type_for_png(saaa_fake, make_proxy_request):
    """
    GIVEN: a PNG file stored in the fake SAAA client
    WHEN:  the proxy endpoint is called
    THEN:  Content-Type is image/png
    """
    contenido = b"\x89PNG\r\n\x1a\n fake png content"
    upload_result = saaa_fake.subir_archivo(
        file_content=contenido,
        nombre_original="imagen.png",
        aplicacion_id="test-app",
        usuario_id="1",
        tipo_archivo_id="1",
    )

    response = make_proxy_request(upload_result.id, saaa_client=saaa_fake)

    assert response.status_code == 200
    assert "image/png" in response.headers.get("content-type", "")


def test_proxy_returns_502_on_saaa_connection_error(saaa_fake):
    """
    GIVEN: a client wrapper that raises SaaaConnectionError
    WHEN:  the proxy endpoint is called
    THEN:  response status is 502 Bad Gateway
    """
    from modules.tramites.domain.exceptions import SaaaConnectionError

    class SaaaConnectionErrorFake:
        """Fake client that simulates SAAA being down."""
        def descargar_archivo(self, archivo_id: str):
            raise SaaaConnectionError("Connection refused")

    from modules.tramites.presentation.controllers.saaa_archivo_proxy_controller import (
        SaaaArchivoProxyController,
    )

    class FakeRequest:
        pass

    controller = SaaaArchivoProxyController(saaa_client=SaaaConnectionErrorFake())
    result = async_to_sync(controller.obtener_archivo_publico)(
        FakeRequest(), saaa_id="any-id"
    )

    assert result.status_code == 502


def test_fake_saaa_client_subir_archivo_returns_full_uuid(saaa_fake):
    """
    GIVEN: FakeSaaaClient.subir_archivo()
    WHEN:  uploading a file
    THEN:  the returned archivo_id is a full UUID (36 chars with hyphens),
           matching what SAAA real produces — NOT a truncated 8-char ID.
           The ID must be parseable as a valid UUID.
    """
    import uuid

    contenido = b"test content for uuid check"
    upload_result = saaa_fake.subir_archivo(
        file_content=contenido,
        nombre_original="documento.pdf",
        aplicacion_id="test-app",
        usuario_id="1",
        tipo_archivo_id="1",
    )

    archivo_id = upload_result.id

    # Full UUID format: 8-4-4-4-12 = 36 chars with 4 hyphens
    assert len(archivo_id) == 36, (
        f"Expected full UUID (36 chars), got {len(archivo_id)} chars: {archivo_id}"
    )

    # Must be parseable as UUID — proves format matches SAAA real
    parsed = uuid.UUID(archivo_id)
    assert str(parsed) == archivo_id

    # The proxy endpoint must be able to retrieve the file using the full ID
    # (round-trip: upload -> use returned ID in proxy -> get back original content)
    proxy_response = saaa_fake.descargar_archivo(archivo_id)
    assert proxy_response.contenido == contenido
