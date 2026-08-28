"""
E2E tests for Expediente GET API.

Tests the /expedientes and /expedientes/{id} endpoints.

Uses ninja_extra.testing.TestClient (sync) per TEST_ARCHITECTURE_CONTRACT.
Controllers are now sync (contrato P3).

URLs: GET /expedientes
      GET /expedientes/{id}
"""
from datetime import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api

from modules.tramites.domain.models import Expediente, ExpedienteArchivo, ExpedienteAntecedente
from modules.tramites.domain.constants import TipoArchivo, EstadoSolicitud


@pytest.fixture
def usuario_creador_exp(db):
    """Create a test user who creates expedientes."""
    User = get_user_model()
    return User.objects.create_user(
        username="operador_exp_list",
        email="operador_exp_list@cip.gob.pe",
        password="testpass123",
        dni="55443321",
        nombres="Expediente",
        apellidos="Operator",
    )


@pytest.fixture
def pdf_file_exp():
    """Create a principal PDF file for expediente creation."""
    return SimpleUploadedFile(
        name="token_principal_pdf___documento_principal.pdf",
        content=b"%PDF-1.4 test content",
        content_type="application/pdf",
    )


def _make_auth_client(user):
    """Create a ninja_extra TestClient with JWT auth for the given user."""
    client = TestClient(api)
    token = AccessToken.for_user(user)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = user
    return client


def _crear_expediente_directo(usuario, numero, **kwargs):
    """Create an Expediente row directly for testing."""
    defaults = dict(
        numero=numero,
        tipo_persona="NATURAL",
        dni="12345678",
        nombres="Juan",
        apellidos="Perez",
        correo="juan@test.com",
        telefono="999888777",
        tipo_documento="SOLICITUD",
        numero_documento=f"DOC-2026-{numero:03d}",
        numero_folios=5,
        asunto=f"Trámite de prueba {numero}",
        fecha_registro=datetime.now(),
        creado_por=usuario,
    )
    defaults.update(kwargs)
    return Expediente.objects.create(**defaults)


# ── GET /expedientes ──────────────────────────────────────────────────────


@pytest.mark.django_db
def test_listar_expedientes_vacio(usuario_creador_exp):
    """
    GIVEN:  no expedientes exist and an authenticated user
    WHEN:   GET /expedientes is called
    THEN:   response status is 200
            AND data.items is an empty list
            AND data.total is 0
    """
    client = _make_auth_client(usuario_creador_exp)
    response = client.get("/expedientes/")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "items" in data["data"]
    assert data["data"]["total"] == 0
    assert data["data"]["items"] == []


@pytest.mark.django_db
def test_listar_expedientes_paginacion(usuario_creador_exp):
    """
    GIVEN:  5 expedientes exist and an authenticated user
    WHEN:   GET /expedientes?page=1&page_size=2 is called
    THEN:   response status is 200
            AND 2 items are returned
            AND total is 5
            AND total_pages is 3
    """
    for i in range(1, 6):
        _crear_expediente_directo(usuario_creador_exp, numero=i, asunto=f"Trámite {i}")

    client = _make_auth_client(usuario_creador_exp)
    response = client.get("/expedientes/", {"page": 1, "page_size": 2})

    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["items"]) == 2, f"Expected 2 items, got {len(data['items'])}"
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 3


@pytest.mark.django_db
def test_listar_expedientes_filtro_busqueda(usuario_creador_exp):
    """
    GIVEN:  3 expedientes exist with different assuntos and an authenticated user
    WHEN:   GET /expedientes?busqueda=Trámite%201 is called
    THEN:   response status is 200
            AND only the expediente with assunto containing 'Trámite 1' is returned
    """
    _crear_expediente_directo(usuario_creador_exp, numero=1, asunto="Trámite especial 1")
    _crear_expediente_directo(usuario_creador_exp, numero=2, asunto="Trámite regular 2")
    _crear_expediente_directo(usuario_creador_exp, numero=3, asunto="Otro assunto 3")

    client = _make_auth_client(usuario_creador_exp)
    response = client.get("/expedientes/", {"busqueda": "especial"})

    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["items"]) == 1, f"Expected 1 item, got {len(data['items'])}"
    assert "especial" in data["items"][0]["asunto"]


@pytest.mark.django_db
def test_listar_expedientes_filtro_año(usuario_creador_exp):
    """
    GIVEN:  expedientes from different years exist and an authenticated user
    WHEN:   GET /expedientes?año=2025 is called
    THEN:   only expedientes from 2025 are returned
    """
    _crear_expediente_directo(
        usuario_creador_exp, numero=1,
        asunto="2025 Trámite",
        fecha_registro=datetime(2025, 6, 15),
    )
    _crear_expediente_directo(
        usuario_creador_exp, numero=2,
        asunto="2026 Trámite",
        fecha_registro=datetime(2026, 6, 15),
    )

    client = _make_auth_client(usuario_creador_exp)
    response = client.get("/expedientes/", {"año": 2025})

    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["items"]) == 1, f"Expected 1 item, got {len(data['items'])}"
    assert data["items"][0]["asunto"] == "2025 Trámite"


@pytest.mark.django_db
def test_listar_expedientes_item_structure(usuario_creador_exp):
    """
    GIVEN:  one expediente exists and an authenticated user
    WHEN:   GET /expedientes is called
    THEN:   each item has required fields including nested expediente data
    """
    _crear_expediente_directo(
        usuario_creador_exp, numero=1,
        dni="12345678",
        nombres="Pedro",
        apellidos="Lopez",
        asunto="Trámite de prueba",
    )

    client = _make_auth_client(usuario_creador_exp)
    response = client.get("/expedientes/")

    assert response.status_code == 200

    data = response.json()["data"]
    item = data["items"][0]

    assert "id" in item
    assert "id_publico" in item
    assert "numero" in item
    assert "tipo_persona" in item
    assert "asunto" in item
    assert "fecha_registro" in item
    assert "numero_documento" in item
    assert "nombres" in item
    assert "apellidos" in item
    assert item["nombres"] == "Pedro"
    assert item["apellidos"] == "Lopez"


# ── GET /expedientes/{id} ────────────────────────────────────────────────


@pytest.mark.django_db
def test_detalle_expediente_no_existe(usuario_creador_exp):
    """
    GIVEN:  no expediente exists with the given ID and an authenticated user
    WHEN:   GET /expedientes/{id_fake} is called
    THEN:   response status is 404
    """
    import uuid
    fake_id = uuid.uuid4()

    client = _make_auth_client(usuario_creador_exp)
    response = client.get(f"/expedientes/{fake_id}")

    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}"
    )


@pytest.mark.django_db
def test_detalle_expediente_basic(usuario_creador_exp):
    """
    GIVEN:  one expediente exists with archivos and an authenticated user
    WHEN:   GET /expedientes/{id} is called
    THEN:   response status is 200
            AND expediente data includes all fields
            AND archivos array is present
            AND antecedentes array is present
    """
    expediente = _crear_expediente_directo(
        usuario_creador_exp, numero=1,
        dni="12345678",
        nombres="Ana",
        apellidos="García",
        asunto="Trámite de detalle",
    )

    # Add an archivo
    ExpedienteArchivo.objects.create(
        expediente=expediente,
        tipo_archivo="PRINCIPAL",
        nombre_original="documento.pdf",
        archivo="expedientes/archivos/test.pdf",
        creado_por=usuario_creador_exp,
    )

    client = _make_auth_client(usuario_creador_exp)
    response = client.get(f"/expedientes/{expediente.id}")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["id"] == str(expediente.id)
    assert data["asunto"] == "Trámite de detalle"
    assert data["nombres"] == "Ana"
    assert data["apellidos"] == "García"
    assert "archivos" in data
    assert len(data["archivos"]) == 1
    assert data["archivos"][0]["tipo_archivo"] == TipoArchivo.PRINCIPAL
    assert "antecedentes" in data


@pytest.mark.django_db
def test_detalle_expediente_con_antecedente(usuario_creador_exp):
    """
    GIVEN:  two expedientes exist with one as antecedent of the other
    WHEN:   GET /expedientes/{id} is called for the newer expediente
    THEN:   response includes the antecedent in the antecedentes array
    """
    antecedente = _crear_expediente_directo(
        usuario_creador_exp, numero=999,
        dni="33333333",
        nombres="Luis",
        apellidos="Pérez",
        asunto="Expediente antecedente",
    )

    nuevo = _crear_expediente_directo(
        usuario_creador_exp, numero=1,
        dni="44444444",
        nombres="María",
        apellidos="Rodríguez",
        asunto="Expediente nuevo",
    )

    ExpedienteAntecedente.objects.create(
        expediente=nuevo,
        antecedente=antecedente,
        categoria="subsanacion",
        observaciones="Documentación incompleta anterior",
    )

    client = _make_auth_client(usuario_creador_exp)
    response = client.get(f"/expedientes/{nuevo.id}")

    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["antecedentes"]) == 1
    assert data["antecedentes"][0]["id_publico"] == antecedente.id_publico
    assert data["antecedentes"][0]["categoria"] == "subsanacion"


@pytest.mark.django_db
def test_detalle_expediente_creado_por(usuario_creador_exp):
    """
    GIVEN:  one expediente exists created by a specific user
    WHEN:   GET /expedientes/{id} is called
    THEN:   creado_por_nombres field contains the creator's full name
    """
    expediente = _crear_expediente_directo(
        usuario_creador_exp, numero=1,
        asunto="Trámite con creador",
    )

    client = _make_auth_client(usuario_creador_exp)
    response = client.get(f"/expedientes/{expediente.id}")

    assert response.status_code == 200

    data = response.json()["data"]
    assert data["creado_por_nombres"] is not None
    assert "Expediente" in data["creado_por_nombres"]
    assert "Operator" in data["creado_por_nombres"]


@pytest.mark.django_db
def test_detalle_expediente_solicitud_asociada(usuario_creador_exp):
    """
    GIVEN:  one expediente exists with a linked Solicitud
    WHEN:   GET /expedientes/{id} is called
    THEN:   solicitud_id, solicitud_estado, and solicitud_prioridad are populated
    """
    from modules.tramites.domain.models import Solicitud
    from modules.tramites.domain.constants import EstadoSolicitud, Prioridad

    expediente = _crear_expediente_directo(
        usuario_creador_exp, numero=1,
        asunto="Trámite con solicitud",
    )

    Solicitud.objects.create(
        expediente=expediente,
        estado=EstadoSolicitud.EN_GESTION,
        prioridad=Prioridad.ALTA,
        fecha_registro=datetime.now(),
        creado_por=usuario_creador_exp,
    )

    client = _make_auth_client(usuario_creador_exp)
    response = client.get(f"/expedientes/{expediente.id}")

    assert response.status_code == 200

    data = response.json()["data"]
    assert data["solicitud_id"] is not None
    assert data["solicitud_estado"] == EstadoSolicitud.EN_GESTION
    assert data["solicitud_prioridad"] == "ALTA"
