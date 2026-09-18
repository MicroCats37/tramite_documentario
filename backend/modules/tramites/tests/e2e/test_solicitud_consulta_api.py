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

from modules.tramites.domain.models import Expediente, Solicitud, SolicitudEstadoHistorial, TipoDocumento
from modules.tramites.domain.constants import EstadoSolicitud
from modules.asignaciones.domain.models import (
    SolicitudAsignacion,
    SolicitudAsignacionPeriodo,
    SolicitudAsignacionUsuario,
)
from modules.asignaciones.domain.constants import EstadoPeriodoOperativo, TipoParticipacion
from modules.usuarios.domain.models import Area, AsignacionUsuario, Cargo


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
    # Resolve tipo_documento: accept either a TipoDocumento instance or a string (nombre).
    tipo_doc_value = kwargs.pop("tipo_documento", "SOLICITUD")
    if isinstance(tipo_doc_value, str):
        tipo_documento = TipoDocumento.objects.get(nombre=tipo_doc_value)
    else:
        tipo_documento = tipo_doc_value

    defaults = dict(
        numero=numero,
        tipo_persona="NATURAL",
        dni="12345678",
        nombres="Juan",
        apellidos="Perez",
        correo="juan@test.com",
        telefono="999888777",
        tipo_documento=tipo_documento,
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


# ── Conversation in detail tests ─────────────────────────────────────────────


@pytest.mark.django_db
def test_detalle_solicitud_incluye_conversacion(usuario_solicitud, area_sol_1):
    """
    GIVEN:  one solicitud created via the API (which creates a conversation)
    WHEN:   GET /solicitudes/{id} is called
    THEN:   response includes conversacion object with id, titulo, estado, fecha_inicio
    """
    from modules.conversaciones.domain.models import SolicitudConversacion, Conversacion
    # Create via API to trigger conversation creation
    exp = _crear_expediente_simple(usuario_solicitud, numero=200, asunto="Trámite con conversación")
    sol = _crear_solicitud_simple(exp, usuario_solicitud, estado="EN_GESTION")

    # Manually create the conversation (since _crear_solicitud_simple bypasses the flow)
    # Note: Conversacion has no estado field - it's computed from fecha_cierre
    conversacion = Conversacion.objects.create(
        titulo=f"Conversación - {exp.id_publico}",
        creada_por=usuario_solicitud,
        fecha_inicio=datetime.now(),
        # fecha_cierre=None means ABIERTA
    )
    SolicitudConversacion.objects.create(
        solicitud=sol,
        conversacion=conversacion,
    )

    client = _make_auth_client(usuario_solicitud)
    response = client.get(f"/solicitudes/{sol.id}")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert "conversacion" in data, "conversacion field should be present"
    assert data["conversacion"] is not None, "conversacion should not be None"
    assert "id" in data["conversacion"]
    assert data["conversacion"]["titulo"] == f"Conversación - {exp.id_publico}"
    assert data["conversacion"]["estado"] == "ABIERTA", (
        f"Expected ABIERTA, got {data['conversacion']['estado']}"
    )
    assert "fecha_inicio" in data["conversacion"]


# ── GET /solicitudes/?mis_areas=true&solo_principal=true ──────────────────


@pytest.mark.django_db
def test_mis_areas_solo_principal_sin_mis_areas_devuelve_400(usuario_solicitud):
    """
    GIVEN: an authenticated user
    WHEN: GET /solicitudes/?solo_principal=true is called without mis_areas
    THEN: returns 400 validation error
    """
    client = _make_auth_client(usuario_solicitud)
    response = client.get("/solicitudes/?solo_principal=true")
    assert response.status_code == 400, (
        f"Expected 400, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_mis_areas_filtra_por_area_usuario(usuario_solicitud, area_sol_1, area_sol_2):
    """
    GIVEN: a user with AsignacionUsuario to area_sol_1 (active),
           a solicitud assigned to area_sol_1 with active period (fecha_fin IS NULL),
           and another solicitud assigned to area_sol_2 (no user assignment)
    WHEN: GET /solicitudes/?mis_areas=true is called
    THEN: returns only the solicitud in the user's assigned area
    """
    # Create cargo and user area assignment to area_sol_1 only
    cargo = Cargo.objects.create(nombre="Cargo Mis Áreas Test")
    AsignacionUsuario.objects.create(
        usuario=usuario_solicitud,
        area=area_sol_1,
        cargo=cargo,
        periodo_inicio=datetime.now().date(),
        periodo_fin=None,
    )

    # Create solicitud in area_sol_1 (user's assigned area) — should appear
    exp1 = _crear_expediente_simple(usuario_solicitud, numero=9001)
    sol1 = _crear_solicitud_simple(exp1, usuario_solicitud)
    asig1 = SolicitudAsignacion.objects.create(
        solicitud=sol1,
        area=area_sol_1,
        fecha_incorporacion=datetime.now(),
        incorporado_por=usuario_solicitud,
    )
    periodo1 = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asig1,
        numero_ciclo=1,
        estado="EN_GESTION",
        tipo_participacion=TipoParticipacion.PRINCIPAL,
        fecha_inicio=datetime.now(),
        fecha_fin=None,  # active period
    )

    # Create solicitud in area_sol_2 (NOT user's area) — should NOT appear
    exp2 = _crear_expediente_simple(usuario_solicitud, numero=9002)
    sol2 = _crear_solicitud_simple(exp2, usuario_solicitud)
    asig2 = SolicitudAsignacion.objects.create(
        solicitud=sol2,
        area=area_sol_2,
        fecha_incorporacion=datetime.now(),
        incorporado_por=usuario_solicitud,
    )
    periodo2 = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asig2,
        numero_ciclo=1,
        estado="EN_GESTION",
        tipo_participacion=TipoParticipacion.PRINCIPAL,
        fecha_inicio=datetime.now(),
        fecha_fin=None,  # active period
    )

    client = _make_auth_client(usuario_solicitud)
    response = client.get("/solicitudes/?mis_areas=true")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )
    data = response.json()["data"]
    ids = [item["id"] for item in data["items"]]
    assert str(sol1.id) in ids, (
        f"solicitud {sol1.id} in user's area should be returned, got ids: {ids}"
    )
    assert str(sol2.id) not in ids, (
        f"solicitud {sol2.id} NOT in user's area should NOT be returned, got ids: {ids}"
    )


@pytest.mark.django_db
def test_mis_areas_solo_principal_filtra_principal(
    usuario_solicitud, area_sol_1, area_sol_2
):
    """
    GIVEN: a user with AsignacionUsuario to area_sol_1,
           a solicitud with PRINCIPAL period in area_sol_1,
           and another solicitud with ADJUNTA period in area_sol_1
    WHEN: GET /solicitudes/?mis_areas=true&solo_principal=true is called
    THEN: returns only the solicitud where user's area is PRINCIPAL
    """
    cargo = Cargo.objects.create(nombre="Cargo Solo Principal Test")
    AsignacionUsuario.objects.create(
        usuario=usuario_solicitud,
        area=area_sol_1,
        cargo=cargo,
        periodo_inicio=datetime.now().date(),
        periodo_fin=None,
    )

    # Solicitud with PRINCIPAL period in area_sol_1 — should appear
    exp1 = _crear_expediente_simple(usuario_solicitud, numero=9011)
    sol1 = _crear_solicitud_simple(exp1, usuario_solicitud)
    asig1 = SolicitudAsignacion.objects.create(
        solicitud=sol1,
        area=area_sol_1,
        fecha_incorporacion=datetime.now(),
        incorporado_por=usuario_solicitud,
    )
    periodo1 = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asig1,
        numero_ciclo=1,
        estado="EN_GESTION",
        tipo_participacion=TipoParticipacion.PRINCIPAL,
        fecha_inicio=datetime.now(),
        fecha_fin=None,
    )

    # Solicitud with ADJUNTA period in area_sol_1 — should NOT appear
    exp2 = _crear_expediente_simple(usuario_solicitud, numero=9012)
    sol2 = _crear_solicitud_simple(exp2, usuario_solicitud)
    asig2 = SolicitudAsignacion.objects.create(
        solicitud=sol2,
        area=area_sol_1,
        fecha_incorporacion=datetime.now(),
        incorporado_por=usuario_solicitud,
    )
    periodo2 = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asig2,
        numero_ciclo=1,
        estado="EN_GESTION",
        tipo_participacion=TipoParticipacion.ADJUNTA,
        fecha_inicio=datetime.now(),
        fecha_fin=None,
    )

    client = _make_auth_client(usuario_solicitud)
    response = client.get("/solicitudes/?mis_areas=true&solo_principal=true")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )
    data = response.json()["data"]
    ids = [item["id"] for item in data["items"]]
    assert str(sol1.id) in ids, (
        f"solicitud {sol1.id} with PRINCIPAL should be returned, got ids: {ids}"
    )
    assert str(sol2.id) not in ids, (
        f"solicitud {sol2.id} with ADJUNTA should NOT be returned, got ids: {ids}"
    )


@pytest.mark.django_db
def test_mis_areas_con_area_id_misma_area(usuario_solicitud, area_sol_1, area_sol_2):
    """
    GIVEN: a user with AsignacionUsuario to area_sol_1,
           two solicitudes: one in area_sol_1 and one in area_sol_2, both with active periods
    WHEN: GET /solicitudes/?mis_areas=true&area_id={area_sol_1}
    THEN: returns only the solicitud in area_sol_1 (mis_areas restricts to user's area,
           area_id further restricts to that specific area which overlaps with user's area)
    """
    cargo = Cargo.objects.create(nombre="Cargo Área ID Mis Áreas Test")
    AsignacionUsuario.objects.create(
        usuario=usuario_solicitud,
        area=area_sol_1,
        cargo=cargo,
        periodo_inicio=datetime.now().date(),
        periodo_fin=None,
    )

    # Solicitud in area_sol_1 (user's area)
    exp1 = _crear_expediente_simple(usuario_solicitud, numero=9031)
    sol1 = _crear_solicitud_simple(exp1, usuario_solicitud)
    asig1 = SolicitudAsignacion.objects.create(
        solicitud=sol1,
        area=area_sol_1,
        fecha_incorporacion=datetime.now(),
        incorporado_por=usuario_solicitud,
    )
    SolicitudAsignacionPeriodo.objects.create(
        asignacion=asig1,
        numero_ciclo=1,
        estado="EN_GESTION",
        fecha_inicio=datetime.now(),
        fecha_fin=None,
    )

    # Solicitud in area_sol_2 (NOT user's area)
    exp2 = _crear_expediente_simple(usuario_solicitud, numero=9032)
    sol2 = _crear_solicitud_simple(exp2, usuario_solicitud)
    asig2 = SolicitudAsignacion.objects.create(
        solicitud=sol2,
        area=area_sol_2,
        fecha_incorporacion=datetime.now(),
        incorporado_por=usuario_solicitud,
    )
    SolicitudAsignacionPeriodo.objects.create(
        asignacion=asig2,
        numero_ciclo=1,
        estado="EN_GESTION",
        fecha_inicio=datetime.now(),
        fecha_fin=None,
    )

    # Query with mis_areas=true AND area_id=area_sol_1 (which IS in user's areas)
    client = _make_auth_client(usuario_solicitud)
    response = client.get(f"/solicitudes/?mis_areas=true&area_id={area_sol_1.id}")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )
    data = response.json()["data"]
    ids = [item["id"] for item in data["items"]]
    assert str(sol1.id) in ids, (
        f"solicitud {sol1.id} in area_sol_1 (user's area) should be returned, got ids: {ids}"
    )
    assert str(sol2.id) not in ids, (
        f"solicitud {sol2.id} in area_sol_2 should NOT be returned (not in user's area AND not area_id filter), got ids: {ids}"
    )


@pytest.mark.django_db
def test_mis_areas_solo_principal_requiere_mis_areas_primero(
    usuario_solicitud, area_sol_1
):
    """
    GIVEN: mis_areas=false and solo_principal=true
    WHEN: GET /solicitudes/?solo_principal=true&mis_areas=false
    THEN: returns 400 (solo_principal without mis_areas is invalid)
    """
    client = _make_auth_client(usuario_solicitud)
    response = client.get("/solicitudes/?solo_principal=true&mis_areas=false")
    assert response.status_code == 400, (
        f"Expected 400, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_creadas_por_mi_filtra_por_creador(
    usuario_solicitud, area_sol_1
):
    """
    GIVEN: two solicitudes — one created by usuario_solicitud and one by another user
    WHEN: GET /solicitudes/?creadas_por_mi=true is called
    THEN: returns only the solicitud created by usuario_solicitud
    """
    # Create another user
    User = get_user_model()
    otro_usuario = User.objects.create_user(
        username="otro_operador",
        email="otro@cip.gob.pe",
        password="testpass123",
        dni="11223344",
        nombres="Otro",
        apellidos="Operador",
    )

    # Solicitud created by usuario_solicitud — should appear
    exp1 = _crear_expediente_simple(usuario_solicitud, numero=9101)
    sol1 = _crear_solicitud_simple(exp1, usuario_solicitud)

    # Solicitud created by another user — should NOT appear
    exp2 = _crear_expediente_simple(otro_usuario, numero=9102)
    sol2 = _crear_solicitud_simple(exp2, otro_usuario)

    client = _make_auth_client(usuario_solicitud)
    response = client.get("/solicitudes/", {"creadas_por_mi": "true"})

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )
    data = response.json()["data"]
    ids = [item["id"] for item in data["items"]]
    assert str(sol1.id) in ids, (
        f"solicitud {sol1.id} created by user should be returned, got ids: {ids}"
    )
    assert str(sol2.id) not in ids, (
        f"solicitud {sol2.id} created by another user should NOT be returned, got ids: {ids}"
    )


@pytest.mark.django_db
def test_creadas_por_mi_false_devuelve_todas(
    usuario_solicitud, area_sol_1
):
    """
    GIVEN: two solicitudes — one created by usuario_solicitud and one by another user
    WHEN: GET /solicitudes/?creadas_por_mi=false is called (default)
    THEN: returns both solicitudes
    """
    User = get_user_model()
    otro_usuario = User.objects.create_user(
        username="otro_operador_2",
        email="otro2@cip.gob.pe",
        password="testpass123",
        dni="22334455",
        nombres="Otro Dos",
        apellidos="Operador",
    )

    exp1 = _crear_expediente_simple(usuario_solicitud, numero=9111)
    sol1 = _crear_solicitud_simple(exp1, usuario_solicitud)

    exp2 = _crear_expediente_simple(otro_usuario, numero=9112)
    sol2 = _crear_solicitud_simple(exp2, otro_usuario)

    client = _make_auth_client(usuario_solicitud)
    response = client.get("/solicitudes/", {"creadas_por_mi": "false"})

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )
    data = response.json()["data"]
    ids = [item["id"] for item in data["items"]]
    assert str(sol1.id) in ids
    assert str(sol2.id) in ids
