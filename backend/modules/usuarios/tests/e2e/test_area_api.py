"""
E2E tests for Area GET API.

Tests the /areas endpoint for listing active areas.

Uses ninja_extra.testing.TestClient (sync) per TEST_ARCHITECTURE_CONTRACT.
Controllers are now sync (contrato P3).

URL: GET /areas
"""
import pytest
from django.contrib.auth import get_user_model

from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api

from modules.usuarios.domain.models import Area


@pytest.fixture
def usuario_test(db):
    """Create a test user for authentication."""
    User = get_user_model()
    return User.objects.create_user(
        username="operador_areas",
        email="operador_areas@cip.gob.pe",
        password="testpass123",
        dni="11223355",
        nombres="Test",
        apellidos="User",
    )


@pytest.fixture
def area_activa(db):
    """Create an active test area."""
    return Area.objects.create(
        nombre="Área Activa Test",
        descripcion="Área activa para tests",
        activo=True,
    )


@pytest.fixture
def area_inactiva(db):
    """Create an inactive test area."""
    return Area.objects.create(
        nombre="Área Inactiva Test",
        descripcion="Área inactiva para tests",
        activo=False,
    )


def _make_auth_client(user):
    """Create a ninja_extra TestClient with JWT auth for the given user."""
    client = TestClient(api)
    token = AccessToken.for_user(user)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = user
    return client


@pytest.mark.django_db
def test_listar_areas_activas(usuario_test, area_activa, area_inactiva):
    """
    GIVEN:  two areas exist (one active, one inactive) and an authenticated user
    WHEN:   GET /areas is called
    THEN:   response status is 200
            AND only the active area is returned
            AND each area includes id, nombre, descripcion, activo
    """
    client = _make_auth_client(usuario_test)
    response = client.get("/areas/")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()

    assert data["success"] is True, "Response should indicate success"
    assert "data" in data, "Response should have 'data' key"

    areas = data["data"]
    assert isinstance(areas, list), "Data should be a list of areas"

    # Only the active area should be returned
    area_ids = [a["id"] for a in areas]
    assert str(area_activa.id) in area_ids, (
        f"Active area {area_activa.id} should be in the list"
    )
    assert str(area_inactiva.id) not in area_ids, (
        f"Inactive area {area_inactiva.id} should NOT be in the list"
    )

    # Verify area structure
    for area in areas:
        assert "id" in area, "Area should have 'id' field"
        assert "nombre" in area, "Area should have 'nombre' field"
        assert "descripcion" in area, "Area should have 'descripcion' field"
        assert "activo" in area, "Area should have 'activo' field"
        assert area["activo"] is True, "Only active areas should be returned"


@pytest.mark.django_db
def test_listar_areas_solo_activas(usuario_test):
    """
    GIVEN:  only active areas exist and an authenticated user
    WHEN:   GET /areas is called
    THEN:   response status is 200
            AND all returned areas have activo=True
    """
    # Create multiple active areas
    Area.objects.create(nombre="Área 1", descripcion="Desc 1", activo=True)
    Area.objects.create(nombre="Área 2", descripcion="Desc 2", activo=True)
    Area.objects.create(nombre="Área 3", descripcion="Desc 3", activo=True)

    # Create one inactive
    Area.objects.create(nombre="Área Inactiva", descripcion="Desc Inact", activo=False)

    client = _make_auth_client(usuario_test)
    response = client.get("/areas/")

    assert response.status_code == 200

    data = response.json()
    areas = data["data"]

    assert len(areas) == 3, f"Expected 3 active areas, got {len(areas)}"
    for area in areas:
        assert area["activo"] is True, "All returned areas should be active"


@pytest.mark.django_db
def test_listar_areas_orden_nombre(usuario_test):
    """
    GIVEN:  multiple active areas with different names and an authenticated user
    WHEN:   GET /areas is called
    THEN:   areas are returned ordered by nombre alphabetically
    """
    Area.objects.create(nombre="Zebra Área", descripcion="Z", activo=True)
    Area.objects.create(nombre="Alpha Área", descripcion="A", activo=True)
    Area.objects.create(nombre="Beta Área", descripcion="B", activo=True)

    client = _make_auth_client(usuario_test)
    response = client.get("/areas/")

    assert response.status_code == 200

    data = response.json()
    areas = data["data"]
    nombres = [a["nombre"] for a in areas]

    assert nombres == sorted(nombres), (
        f"Areas should be ordered by nombre. Got: {nombres}"
    )
