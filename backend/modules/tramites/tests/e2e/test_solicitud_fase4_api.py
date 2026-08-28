"""
E2E tests for Solicitud Fase 4 — Operación de áreas.

Tests cover:
- 4.1: POST /solicitudes/{id}/areas — incorporar área a una solicitud existente

Uses ninja_extra.testing.TestClient (sync) per TEST_ARCHITECTURE_CONTRACT.
Controllers are async but django.test.Client handles them correctly.
"""
from datetime import datetime

import pytest
from django.contrib.auth import get_user_model

from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api

from modules.tramites.domain.models import (
    Expediente,
    Solicitud,
    SolicitudEstadoHistorial,
)
from modules.asignaciones.domain.models import (
    SolicitudAsignacion,
    SolicitudAsignacionPeriodo,
)
from modules.usuarios.domain.models import Area


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def usuario_operador(db):
    """Create a test user for area operations."""
    User = get_user_model()
    return User.objects.create_user(
        username="operador_area",
        email="operador_area@cip.gob.pe",
        password="testpass123",
        dni="11223344",
        nombres="Carlos",
        apellidos="Ramirez",
    )


@pytest.fixture
def area_arquitectura(db):
    """Create Arquitectura area."""
    return Area.objects.create(
        nombre="Arquitectura",
        descripcion="Área de Arquitectura",
        activo=True,
    )


@pytest.fixture
def area_estructuras(db):
    """Create Estructuras area."""
    return Area.objects.create(
        nombre="Estructuras",
        descripcion="Área de Estructuras",
        activo=True,
    )


@pytest.fixture
def area_inactiva(db):
    """Create an inactive area."""
    return Area.objects.create(
        nombre="Área Inactiva",
        descripcion="Área inactiva",
        activo=False,
    )


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_auth_client(user):
    """Create a ninja_extra TestClient with JWT auth for the given user."""
    client = TestClient(api)
    token = AccessToken.for_user(user)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = user
    return client


def _crear_solicitud_registrada(usuario, expediente, area_asignada=None):
    """
    Create a Solicitud in REGISTRADA state, optionally with one area already assigned.
    Returns the Solicitud instance.
    """
    ahora = datetime.now()
    solicitud = Solicitud.objects.create(
        expediente=expediente,
        estado="REGISTRADA",
        prioridad="MEDIA",
        fecha_registro=ahora,
        creado_por=usuario,
    )
    SolicitudEstadoHistorial.objects.create(
        solicitud=solicitud,
        estado_anterior=None,
        estado_nuevo="REGISTRADA",
        cambiado_por=usuario,
        fecha_cambio=ahora,
        motivo="Creación",
        origen="CREACION",
    )
    if area_asignada:
        asignacion = SolicitudAsignacion.objects.create(
            solicitud=solicitud,
            area=area_asignada,
            fecha_incorporacion=ahora,
            incorporado_por=usuario,
        )
        SolicitudAsignacionPeriodo.objects.create(
            asignacion=asignacion,
            numero_ciclo=1,
            tipo_participacion="PRINCIPAL",
            estado="PENDIENTE",
            fecha_inicio=ahora,
            iniciado_por=usuario,
        )
    return solicitud


def _crear_solicitud_en_gestion(usuario, expediente, area_asignada=None):
    """
    Create a Solicitud in EN_GESTION state, optionally with one area already assigned.
    Returns the Solicitud instance.
    """
    ahora = datetime.now()
    solicitud = Solicitud.objects.create(
        expediente=expediente,
        estado="EN_GESTION",
        prioridad="MEDIA",
        fecha_registro=ahora,
        fecha_inicio_gestion=ahora,
        creado_por=usuario,
    )
    SolicitudEstadoHistorial.objects.create(
        solicitud=solicitud,
        estado_anterior=None,
        estado_nuevo="REGISTRADA",
        cambiado_por=usuario,
        fecha_cambio=ahora,
        origen="CREACION",
    )
    SolicitudEstadoHistorial.objects.create(
        solicitud=solicitud,
        estado_anterior="REGISTRADA",
        estado_nuevo="EN_GESTION",
        cambiado_por=usuario,
        fecha_cambio=ahora,
        origen="CAMBIO_ESTADO",
    )
    if area_asignada:
        asignacion = SolicitudAsignacion.objects.create(
            solicitud=solicitud,
            area=area_asignada,
            fecha_incorporacion=ahora,
            incorporado_por=usuario,
        )
        SolicitudAsignacionPeriodo.objects.create(
            asignacion=asignacion,
            numero_ciclo=1,
            tipo_participacion="PRINCIPAL",
            estado="PENDIENTE",
            fecha_inicio=ahora,
            iniciado_por=usuario,
        )
    return solicitud


# ── Task 4.1: POST /solicitudes/{id}/areas — happy paths ───────────────────

@pytest.mark.django_db
def test_incorporar_area_a_solicitud_registrada_transiciona_a_en_gestion(
    usuario_operador, area_arquitectura, area_estructuras
):
    """
    GIVEN: a Solicitud in REGISTRADA state (no areas) and two areas
    WHEN:  POST /solicitudes/{id}/areas is called with one area
    THEN:  response status is 200
            AND Solicitud.estado == EN_GESTION
            AND Solicitud.fecha_inicio_gestion is set
            AND a SolicitudEstadoHistorial record shows REGISTRADA → EN_GESTION
            AND a SolicitudAsignacion record exists
            AND a SolicitudAsignacionPeriodo record exists (ciclo=1, PENDIENTE)
    """
    # Setup: create expediente + solicitud REGISTRADA
    expediente = Expediente.objects.create(
        numero=1,
        tipo_persona="NATURAL",
        dni="12345678",
        nombres="Juan",
        apellidos="Perez",
        correo="juan@test.com",
        telefono="999888777",
        tipo_documento="SOLICITUD",
        numero_documento="DOC-2026-F4-001",
        numero_folios=5,
        asunto="Trámite para incorporar área",
        fecha_registro=datetime.now(),
        creado_por=usuario_operador,
    )
    solicitud = _crear_solicitud_registrada(usuario_operador, expediente)

    payload = {
        "area_id": str(area_arquitectura.id),
        "tipo_participacion": "PRINCIPAL",
        "observacion": "Primera área asignada",
    }

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/solicitudes/{solicitud.id}/areas",
        json=payload,
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["estado"] == "EN_GESTION", (
        f"Expected EN_GESTION, got {data['estado']}"
    )
    assert data["fecha_inicio_gestion"] is not None, (
        "fecha_inicio_gestion should be set after first area incorporation"
    )

    # Verify DB state
    solicitud.refresh_from_db()
    assert solicitud.estado == "EN_GESTION"
    assert solicitud.fecha_inicio_gestion is not None

    # Verify historial
    historial = list(
        SolicitudEstadoHistorial.objects.filter(solicitud=solicitud)
        .order_by("fecha_cambio")
        .values_list("estado_nuevo", flat=True)
    )
    assert historial == ["REGISTRADA", "EN_GESTION"], (
        f"Expected [REGISTRADA, EN_GESTION], got {historial}"
    )

    # Verify asignacion
    assert SolicitudAsignacion.objects.filter(solicitud=solicitud, area=area_arquitectura).exists()
    asignacion = SolicitudAsignacion.objects.get(solicitud=solicitud, area=area_arquitectura)

    # Verify periodo
    assert SolicitudAsignacionPeriodo.objects.filter(
        asignacion=asignacion,
        numero_ciclo=1,
        estado="PENDIENTE",
    ).exists()


@pytest.mark.django_db
def test_incorporar_area_a_solicitud_en_gestion(
    usuario_operador, area_arquitectura, area_estructuras
):
    """
    GIVEN: a Solicitud in EN_GESTION state with one area already assigned
    WHEN:  POST /solicitudes/{id}/areas is called with a second area
    THEN:  response status is 200
            AND Solicitud.estado stays EN_GESTION (no transition)
            AND a new SolicitudAsignacion record exists
            AND a new SolicitudAsignacionPeriodo record exists (ciclo=1, PENDIENTE)
    """
    expediente = Expediente.objects.create(
        numero=2,
        tipo_persona="NATURAL",
        dni="22345678",
        nombres="Pedro",
        apellidos="Lopez",
        correo="pedro@test.com",
        telefono="988877766",
        tipo_documento="SOLICITUD",
        numero_documento="DOC-2026-F4-002",
        numero_folios=3,
        asunto="Trámite con área existente",
        fecha_registro=datetime.now(),
        creado_por=usuario_operador,
    )
    # Create with Arquitectura already assigned
    solicitud = _crear_solicitud_en_gestion(usuario_operador, expediente, area_arquitectura)

    payload = {
        "area_id": str(area_estructuras.id),
        "tipo_participacion": "ADJUNTA",
        "observacion": "Segunda área",
    }

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/solicitudes/{solicitud.id}/areas",
        json=payload,
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["estado"] == "EN_GESTION", (
        f"Expected EN_GESTION (no change), got {data['estado']}"
    )

    # Verify new asignacion
    assert SolicitudAsignacion.objects.filter(solicitud=solicitud, area=area_estructuras).exists()
    asignacion = SolicitudAsignacion.objects.get(solicitud=solicitud, area=area_estructuras)

    # Verify periodo
    assert SolicitudAsignacionPeriodo.objects.filter(
        asignacion=asignacion,
        numero_ciclo=1,
        tipo_participacion="ADJUNTA",
        estado="PENDIENTE",
    ).exists()


@pytest.mark.django_db
def test_incorporar_area_respuesta_incluye_asignaciones(
    usuario_operador, area_arquitectura, area_estructuras
):
    """
    GIVEN: a Solicitud in REGISTRADA with no areas
    WHEN:  POST /solicitudes/{id}/areas is called
    THEN:  response includes asignaciones array
            AND each asignacion has area_id, area_nombre, tipo_participacion
    """
    expediente = Expediente.objects.create(
        numero=3,
        tipo_persona="NATURAL",
        dni="32345678",
        nombres="Maria",
        apellidos="Garcia",
        correo="maria@test.com",
        telefono="977766655",
        tipo_documento="SOLICITUD",
        numero_documento="DOC-2026-F4-003",
        numero_folios=4,
        asunto="Verificar respuesta",
        fecha_registro=datetime.now(),
        creado_por=usuario_operador,
    )
    solicitud = _crear_solicitud_registrada(usuario_operador, expediente)

    payload = {
        "area_id": str(area_arquitectura.id),
        "tipo_participacion": "PRINCIPAL",
        "observacion": None,
    }

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/solicitudes/{solicitud.id}/areas",
        json=payload,
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert "asignaciones" in data, "Response should include asignaciones"
    assert len(data["asignaciones"]) == 1, (
        f"Expected 1 asignacion, got {len(data['asignaciones'])}"
    )
    asig = data["asignaciones"][0]
    assert asig["area_id"] == str(area_arquitectura.id)
    assert asig["area_nombre"] == area_arquitectura.nombre
    assert asig["tipo_participacion"] == "PRINCIPAL"


# ── Task 4.1: Error paths ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_incorporar_area_ya_asignada_devuelve_409(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a Solicitud with area_arquitectura already assigned
    WHEN:  POST /solicitudes/{id}/areas is called with the same area
    THEN:  response status is 409
            AND error code is Conflict
    """
    expediente = Expediente.objects.create(
        numero=4,
        tipo_persona="NATURAL",
        dni="42345678",
        nombres="Ana",
        apellidos="Martinez",
        correo="ana@test.com",
        telefono="966655544",
        tipo_documento="SOLICITUD",
        numero_documento="DOC-2026-F4-004",
        numero_folios=2,
        asunto="Área duplicada",
        fecha_registro=datetime.now(),
        creado_por=usuario_operador,
    )
    solicitud = _crear_solicitud_en_gestion(usuario_operador, expediente, area_arquitectura)

    payload = {
        "area_id": str(area_arquitectura.id),
        "tipo_participacion": "PRINCIPAL",
        "observacion": None,
    }

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/solicitudes/{solicitud.id}/areas",
        json=payload,
    )

    assert response.status_code == 409, (
        f"Expected 409, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_incorporar_area_solicitud_no_existe_devuelve_404(usuario_operador, area_arquitectura):
    """
    GIVEN: a non-existent Solicitud UUID
    WHEN:  POST /solicitudes/{id}/areas is called
    THEN:  response status is 404
    """
    from uuid import uuid4

    payload = {
        "area_id": str(area_arquitectura.id),
        "tipo_participacion": "PRINCIPAL",
        "observacion": None,
    }

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/solicitudes/{uuid4()}/areas",
        json=payload,
    )

    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_incorporar_area_no_existe_devuelve_404(usuario_operador):
    """
    GIVEN: a valid Solicitud but a non-existent Area UUID
    WHEN:  POST /solicitudes/{id}/areas is called
    THEN:  response status is 404
    """
    from uuid import uuid4

    expediente = Expediente.objects.create(
        numero=5,
        tipo_persona="NATURAL",
        dni="52345678",
        nombres="Luis",
        apellidos="Diaz",
        correo="luis@test.com",
        telefono="955544433",
        tipo_documento="SOLICITUD",
        numero_documento="DOC-2026-F4-005",
        numero_folios=1,
        asunto="Área inexistente",
        fecha_registro=datetime.now(),
        creado_por=usuario_operador,
    )
    solicitud = _crear_solicitud_registrada(usuario_operador, expediente)

    payload = {
        "area_id": str(uuid4()),
        "tipo_participacion": "PRINCIPAL",
        "observacion": None,
    }

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/solicitudes/{solicitud.id}/areas",
        json=payload,
    )

    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_incorporar_area_solicitud_finalizada_devuelve_409(usuario_operador, area_arquitectura):
    """
    GIVEN: a Solicitud in FINALIZADA state
    WHEN:  POST /solicitudes/{id}/areas is called
    THEN:  response status is 409
    """
    expediente = Expediente.objects.create(
        numero=6,
        tipo_persona="NATURAL",
        dni="62345678",
        nombres="Elena",
        apellidos="Ruiz",
        correo="elena@test.com",
        telefono="944433322",
        tipo_documento="SOLICITUD",
        numero_documento="DOC-2026-F4-006",
        numero_folios=3,
        asunto="Solicitud finalizada",
        fecha_registro=datetime.now(),
        creado_por=usuario_operador,
    )
    ahora = datetime.now()
    solicitud = Solicitud.objects.create(
        expediente=expediente,
        estado="FINALIZADA",
        prioridad="MEDIA",
        fecha_registro=ahora,
        fecha_cierre=ahora,
        creado_por=usuario_operador,
    )

    payload = {
        "area_id": str(area_arquitectura.id),
        "tipo_participacion": "PRINCIPAL",
        "observacion": None,
    }

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/solicitudes/{solicitud.id}/areas",
        json=payload,
    )

    assert response.status_code == 409, (
        f"Expected 409, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_incorporar_area_solicitud_anulada_devuelve_409(usuario_operador, area_arquitectura):
    """
    GIVEN: a Solicitud in ANULADA state
    WHEN:  POST /solicitudes/{id}/areas is called
    THEN:  response status is 409
    """
    expediente = Expediente.objects.create(
        numero=7,
        tipo_persona="NATURAL",
        dni="72345678",
        nombres="Roberto",
        apellidos="Soto",
        correo="roberto@test.com",
        telefono="933322211",
        tipo_documento="SOLICITUD",
        numero_documento="DOC-2026-F4-007",
        numero_folios=2,
        asunto="Solicitud anulada",
        fecha_registro=datetime.now(),
        creado_por=usuario_operador,
    )
    ahora = datetime.now()
    solicitud = Solicitud.objects.create(
        expediente=expediente,
        estado="ANULADA",
        prioridad="MEDIA",
        fecha_registro=ahora,
        creado_por=usuario_operador,
    )

    payload = {
        "area_id": str(area_arquitectura.id),
        "tipo_participacion": "PRINCIPAL",
        "observacion": None,
    }

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/solicitudes/{solicitud.id}/areas",
        json=payload,
    )

    assert response.status_code == 409, (
        f"Expected 409, got {response.status_code}: {response.content}"
    )
