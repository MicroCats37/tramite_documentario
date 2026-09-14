"""
E2E tests for TipoDocumento GET API.

Tests the /tipos-documento endpoint for listing all tipos de documento.

Uses ninja_extra.testing.TestClient (sync) per TEST_ARCHITECTURE_CONTRACT.
Controllers are async (contrato P3) — use sync_to_async in implementation.

URL: GET /tipos-documento
"""
import pytest
from django.contrib.auth import get_user_model

from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api

from modules.tramites.domain.models import TipoDocumento


@pytest.fixture
def usuario_test(db):
    """Create a test user for authentication."""
    User = get_user_model()
    return User.objects.create_user(
        username="operador_tipos_doc",
        email="operador_tiposdoc@cip.gob.pe",
        password="testpass123",
        dni="11223366",
        nombres="Test",
        apellidos="User",
    )


def _make_auth_client(user):
    """Create a ninja_extra TestClient with JWT auth for the given user."""
    client = TestClient(api)
    token = AccessToken.for_user(user)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = user
    return client


@pytest.mark.django_db
def test_listar_tipos_documento(usuario_test):
    """
    GIVEN:  seeded TipoDocumento records exist and an authenticated user
    WHEN:   GET /tipos-documento is called
    THEN:   response status is 200
            AND all seeded tipos are returned
            AND each tipo includes id, nombre, descripcion
    """
    client = _make_auth_client(usuario_test)
    response = client.get("/tipos-documento/")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()

    assert data["success"] is True, "Response should indicate success"
    assert "data" in data, "Response should have 'data' key"

    tipos = data["data"]
    assert isinstance(tipos, list), "Data should be a list of tipos"

    # Verify seeded values are present (OFICIO, CARTA, SOLICITUD, etc.)
    nombres = [t["nombre"] for t in tipos]
    assert "OFICIO" in nombres, "OFICIO should be in the list"
    assert "CARTA" in nombres, "CARTA should be in the list"
    assert "SOLICITUD" in nombres, "SOLICITUD should be in the list"

    # Verify structure
    for tipo in tipos:
        assert "id" in tipo, "Tipo should have 'id' field"
        assert "nombre" in tipo, "Tipo should have 'nombre' field"
        assert "descripcion" in tipo, "Tipo should have 'descripcion' field"
        # Verify UUID format
        assert len(tipo["id"]) == 36, f"id should be UUID format, got {tipo['id']}"


@pytest.mark.django_db
def test_listar_tipos_documento_orden_nombre(usuario_test):
    """
    GIVEN:  multiple tipos de documento exist and an authenticated user
    WHEN:   GET /tipos-documento is called
    THEN:   tipos are returned ordered by nombre alphabetically
    """
    client = _make_auth_client(usuario_test)
    response = client.get("/tipos-documento/")

    assert response.status_code == 200

    data = response.json()
    tipos = data["data"]
    nombres = [t["nombre"] for t in tipos]

    assert nombres == sorted(nombres), (
        f"Tipos should be ordered by nombre. Got: {nombres}"
    )


@pytest.mark.django_db
def test_listar_tipos_documento_todos_los_semillas(usuario_test):
    """
    GIVEN:  all 9 seeded TipoDocumento records exist and an authenticated user
    WHEN:   GET /tipos-documento is called
    THEN:   exactly 9 tipos are returned
    """
    client = _make_auth_client(usuario_test)
    response = client.get("/tipos-documento/")

    assert response.status_code == 200

    data = response.json()
    tipos = data["data"]

    expected_nombres = {
        "OFICIO", "CARTA", "SOLICITUD", "MEMORANDO",
        "INFORME", "EXPEDIENTE", "RECIBO", "CERTIFICADO", "OTRO",
    }
    returned_nombres = {t["nombre"] for t in tipos}

    assert len(tipos) == 9, f"Expected 9 tipos, got {len(tipos)}"
    assert returned_nombres == expected_nombres, (
        f"Expected {expected_nombres}, got {returned_nombres}"
    )
