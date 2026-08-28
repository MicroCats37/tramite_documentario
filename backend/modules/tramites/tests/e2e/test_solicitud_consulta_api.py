"""
E2E tests for Solicitud GET API.

Tests the /solicitudes, /solicitudes/{id}, and /solicitudes/{id}/estado-operativo endpoints.

Uses ninja_extra.testing.TestClient (sync) per TEST_ARCHITECTURE_CONTRACT.
Controllers are now sync (contrato P3).

URLs: GET /solicitudes
      GET /solicitudes/{id}
      GET /solicitudes/{id}/estado-operativo
"""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api

from modules.tramites.domain.models import Expediente, Solicitud, SolicitudEstadoHistorial
from modules.tramites.domain.constants import EstadoSolicitud
from modules.asignaciones.domain.models import (
    SolicitudAsignacion,
    SolicitudAsignacionPeriodo,
    SolicitudAsignacionUsuario,
)
from modules.asignaciones.domain.constants import EstadoPeriodoOperativo
from modules.usuarios.domain.models import Area


@pytest.fixture
def usuario_solicitud(db):
    """Create a test user for Solicitud tests."""
    User = get_user_model()
    return User.objects.create_user(
        username="operador_solicitud",
        email="operador_solicitud@cip.gob.pe",
        password="testpass123",
        dni="66778899",
        nombres="Solicitud",
        apellidos="Operator",
    )


@pytest.fixture
def area_sol_1(db):
    """Create first test area."""
    return Area.objects.create(nombre="Área de Prueba 1", activo=True)


@pytest.fixture
def area_sol_2(db):
    """Create second test area."""
    return Area.objects.create(nombre="Área de Prueba 2", activo=True)


def _make_auth_client(user):
    """Create a ninja_extra TestClient with JWT auth for the given user."""
    client = TestClient(api)
    token = AccessToken.for_user(user)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = user
    return client


def _crear_expediente_simple(usuario, numero, **kwargs):
    """Create an Expediente row directly."""
    defaults = dict(
        numero=numero,
        tipo_persona="NATURAL",
        dni="12345678",
        nombres="Juan",
        apellidos="Perez",
        correo="juan@test.com",
        telefono="999888777",
        tipo_documento="SOLICITUD",
        numero_documento=f"DOC-SOL-{numero:03d}",
        numero_folios=5,
        asunto=f"Trámite de prueba {numero}",
        fecha_registro=datetime.now(),
        creado_por=usuario,
    )
    defaults.update(kwargs)
    return Expediente.objects.create(**defaults)


def _crear_solicitud_simple(expediente, usuario, estado="REGISTRADA", prioridad="MEDIA", **kwargs):
    """Create a Solicitud row directly."""
    from modules.tramites.domain.constants import EstadoSolicitud, Prioridad
    defaults = dict(
        expediente=expediente,
        estado=estado,
        prioridad=prioridad,
        fecha_registro=datetime.now(),
        creado_por=usuario,
    )
    defaults.update(kwargs)
    return Solicitud.objects.create(**defaults)


# ── GET /solicitudes ──────────────────────────────────────────────────────


@pytest.mark.django_db
def test_listar_solicitudes_vacio(usuario_solicitud):
    """
    GIVEN:  no solicitudes exist and an authenticated user
    WHEN:   GET /solicitudes is called
    THEN:   response status is 200
            AND items is empty
            AND total is 0
    """
    client = _make_auth_client(usuario_solicitud)
    response = client.get("/solicitudes/")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.django_db
def test_listar_solicitudes_paginacion(usuario_solicitud, area_sol_1):
    """
    GIVEN:  5 solicitudes exist and an authenticated user
    WHEN:   GET /solicitudes?page=1&page_size=2 is called
    THEN:   response status is 200
            AND 2 items are returned
            AND total is 5
            AND total_pages is 3
    """
    for i in range(1, 6):
        exp = _crear_expediente_simple(usuario_solicitud, numero=i, asunto=f"Trámite {i}")
        _crear_solicitud_simple(exp, usuario_solicitud)

    client = _make_auth_client(usuario_solicitud)
    response = client.get("/solicitudes/", {"page": 1, "page_size": 2})

    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 3


@pytest.mark.django_db
def test_listar_solicitudes_filtro_estado(usuario_solicitud, area_sol_1):
    """
    GIVEN:  solicitudes with different estados exist
    WHEN:   GET /solicitudes?estado=REGISTRADA is called
    THEN:   only solicitudes in REGISTRADA state are returned
    """
    exp1 = _crear_expediente_simple(usuario_solicitud, numero=1)
    exp2 = _crear_expediente_simple(usuario_solicitud, numero=2)
    _crear_solicitud_simple(exp1, usuario_solicitud, estado="REGISTRADA")
    _crear_solicitud_simple(exp2, usuario_solicitud, estado="EN_GESTION")

    client = _make_auth_client(usuario_solicitud)
    response = client.get("/solicitudes/", {"estado": "REGISTRADA"})

    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["items"]) == 1
    assert data["items"][0]["estado"] == EstadoSolicitud.REGISTRADA


@pytest.mark.django_db
def test_listar_solicitudes_filtro_me(usuario_solicitud, area_sol_1):
    """
    GIVEN:  one solicitud where the user participates as assignee
    WHEN:   GET /solicitudes?me=true is called
    THEN:   only solicitudes where the user participates are returned
    """
    exp = _crear_expediente_simple(usuario_solicitud, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_solicitud, estado="EN_GESTION")

    # Create assignment with area
    asignacion = SolicitudAsignacion.objects.create(
        solicitud=sol,
        area=area_sol_1,
        fecha_incorporacion=datetime.now(),
        incorporado_por=usuario_solicitud,
    )

    # Create period with the user as participant
    periodo = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        estado="EN_GESTION",
        fecha_inicio=datetime.now(),
    )

    SolicitudAsignacionUsuario.objects.create(
        periodo=periodo,
        usuario=usuario_solicitud,
        rol="Responsable",
        fecha_inicio=datetime.now(),
    )

    client = _make_auth_client(usuario_solicitud)
    response = client.get("/solicitudes/", {"me": "true"})

    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(sol.id)


@pytest.mark.django_db
def test_listar_solicitudes_item_structure(usuario_solicitud, area_sol_1):
    """
    GIVEN:  one solicitud with areas exists
    WHEN:   GET /solicitudes is called
    THEN:   each item has required fields including areas_activas
    """
    exp = _crear_expediente_simple(
        usuario_solicitud, numero=1,
        nombres="Pedro", apellidos="Lopez",
    )
    sol = _crear_solicitud_simple(exp, usuario_solicitud, prioridad="ALTA")

    # Add assignment with period
    asignacion = SolicitudAsignacion.objects.create(
        solicitud=sol,
        area=area_sol_1,
        fecha_incorporacion=datetime.now(),
        incorporado_por=usuario_solicitud,
    )
    SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        tipo_participacion="PRINCIPAL",
        estado="PENDIENTE",
        fecha_inicio=datetime.now(),
    )

    client = _make_auth_client(usuario_solicitud)
    response = client.get("/solicitudes/")

    assert response.status_code == 200

    data = response.json()["data"]
    item = data["items"][0]

    assert "id" in item
    assert "expediente" in item
    assert "estado" in item
    assert "prioridad" in item
    assert "fecha_registro" in item
    assert "areas_activas" in item
    # Nested expediente object has the expediente data
    exp = item["expediente"]
    assert "id_publico" in exp
    assert "asunto" in exp
    assert "nombres" in exp
    assert "apellidos" in exp
    assert exp["nombres"] == "Pedro"
    assert exp["apellidos"] == "Lopez"
    assert item["prioridad"] == "ALTA"


# ── GET /solicitudes/{id} ────────────────────────────────────────────────


@pytest.mark.django_db
def test_detalle_solicitud_no_existe(usuario_solicitud):
    """
    GIVEN:  no solicitud exists with the given ID
    WHEN:   GET /solicitudes/{id_fake} is called
    THEN:   response status is 404
    """
    import uuid
    fake_id = uuid.uuid4()

    client = _make_auth_client(usuario_solicitud)
    response = client.get(f"/solicitudes/{fake_id}")

    assert response.status_code == 404


@pytest.mark.django_db
def test_detalle_solicitud_basic(usuario_solicitud, area_sol_1):
    """
    GIVEN:  one solicitud with areas exists
    WHEN:   GET /solicitudes/{id} is called
    THEN:   response status is 200
            AND includes solicitud fields, expediente, historial_global, asignaciones
    """
    exp = _crear_expediente_simple(usuario_solicitud, numero=1, asunto="Trámite detalle")
    sol = _crear_solicitud_simple(exp, usuario_solicitud, estado="EN_GESTION")

    # Add assignment
    asignacion = SolicitudAsignacion.objects.create(
        solicitud=sol,
        area=area_sol_1,
        fecha_incorporacion=datetime.now(),
        incorporado_por=usuario_solicitud,
    )
    SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        tipo_participacion="PRINCIPAL",
        estado="EN_GESTION",
        fecha_inicio=datetime.now(),
    )

    client = _make_auth_client(usuario_solicitud)
    response = client.get(f"/solicitudes/{sol.id}")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["id"] == str(sol.id)
    assert data["estado"] == EstadoSolicitud.EN_GESTION
    assert "expediente" in data
    assert data["expediente"]["asunto"] == "Trámite detalle"
    assert "historial_global" in data
    assert "asignaciones" in data
    assert len(data["asignaciones"]) == 1
    assert data["asignaciones"][0]["area_nombre"] == "Área de Prueba 1"


@pytest.mark.django_db
def test_detalle_solicitud_con_periodos(usuario_solicitud, area_sol_1):
    """
    GIVEN:  one solicitud with a period exists
    WHEN:   GET /solicitudes/{id} is called
    THEN:   asignaciones include periodos array with correct data
    """
    exp = _crear_expediente_simple(usuario_solicitud, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_solicitud)

    asignacion = SolicitudAsignacion.objects.create(
        solicitud=sol,
        area=area_sol_1,
        fecha_incorporacion=datetime.now(),
        incorporado_por=usuario_solicitud,
    )
    periodo = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        tipo_participacion="PRINCIPAL",
        estado="EN_GESTION",
        fecha_inicio=datetime.now(),
    )

    client = _make_auth_client(usuario_solicitud)
    response = client.get(f"/solicitudes/{sol.id}")

    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["asignaciones"][0]["periodos"]) == 1
    periodo_data = data["asignaciones"][0]["periodos"][0]
    assert periodo_data["numero_ciclo"] == 1
    assert periodo_data["estado"] == EstadoPeriodoOperativo.EN_GESTION


# ── GET /solicitudes/{id}/estado-operativo ───────────────────────────────


@pytest.mark.django_db
def test_estado_operativo_no_existe(usuario_solicitud):
    """
    GIVEN:  no solicitud exists with the given ID
    WHEN:   GET /solicitudes/{id_fake}/estado-operativo is called
    THEN:   response status is 404
    """
    import uuid
    fake_id = uuid.uuid4()

    client = _make_auth_client(usuario_solicitud)
    response = client.get(f"/solicitudes/{fake_id}/estado-operativo")

    assert response.status_code == 404


@pytest.mark.django_db
def test_estado_operativo_basico(usuario_solicitud, area_sol_1, area_sol_2):
    """
    GIVEN:  one solicitud with two areas (one in PENDIENTE, one in EN_GESTION) exists
    WHEN:   GET /solicitudes/{id}/estado-operativo is called
    THEN:   response status is 200
            AND total_areas is 2
            AND areas_pendientes is 1
            AND areas_en_gestion is 1
    """
    exp = _crear_expediente_simple(usuario_solicitud, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_solicitud)

    # Create two assignments with different period states
    for area, estado in [(area_sol_1, "PENDIENTE"), (area_sol_2, "EN_GESTION")]:
        asignacion = SolicitudAsignacion.objects.create(
            solicitud=sol,
            area=area,
            fecha_incorporacion=datetime.now(),
            incorporado_por=usuario_solicitud,
        )
        SolicitudAsignacionPeriodo.objects.create(
            asignacion=asignacion,
            numero_ciclo=1,
            tipo_participacion="PRINCIPAL",
            estado=estado,
            fecha_inicio=datetime.now(),
        )

    client = _make_auth_client(usuario_solicitud)
    response = client.get(f"/solicitudes/{sol.id}/estado-operativo")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["total_areas"] == 2
    assert data["areas_pendientes"] == 1
    assert data["areas_en_gestion"] == 1
    assert data["areas_cerradas"] == 0


@pytest.mark.django_db
def test_estado_operativo_vencida(usuario_solicitud, area_sol_1):
    """
    GIVEN:  one solicitud with fecha_limite in the past and estado not FINALIZADA
    WHEN:   GET /solicitudes/{id}/estado-operativo is called
    THEN:   vencida is True
    """
    exp = _crear_expediente_simple(usuario_solicitud, numero=1)
    _crear_solicitud_simple(
        exp, usuario_solicitud,
        estado="EN_GESTION",
        fecha_limite=datetime.now() - timedelta(days=1),
    )

    client = _make_auth_client(usuario_solicitud)
    response = client.get(f"/solicitudes/{exp.solicitud.id}/estado-operativo")

    assert response.status_code == 200

    data = response.json()["data"]
    assert data["vencida"] is True


@pytest.mark.django_db
def test_estado_operativo_no_vencida(usuario_solicitud, area_sol_1):
    """
    GIVEN:  one solicitud with fecha_limite in the future and estado EN_GESTION
    WHEN:   GET /solicitudes/{id}/estado-operativo is called
    THEN:   vencida is False
    """
    exp = _crear_expediente_simple(usuario_solicitud, numero=1)
    _crear_solicitud_simple(
        exp, usuario_solicitud,
        estado="EN_GESTION",
        fecha_limite=datetime.now() + timedelta(days=5),
    )

    client = _make_auth_client(usuario_solicitud)
    response = client.get(f"/solicitudes/{exp.solicitud.id}/estado-operativo")

    assert response.status_code == 200

    data = response.json()["data"]
    assert data["vencida"] is False
