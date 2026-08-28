"""
E2E tests for Periodo Fase 5 — Respuestas.

Tests cover:
- 5.1: POST /periodos/{id}/respuestas — crear respuesta en estado BORRADOR

Uses ninja_extra.testing.TestClient (sync) per TEST_ARCHITECTURE_CONTRACT.
Controllers are async but django.test.Client handles them correctly (per django-app-architecture-contract 2.1).
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
    SolicitudAsignacionPeriodoEstadoHistorial,
    SolicitudAsignacionRespuesta,
)
from modules.asignaciones.domain.constants import (
    EstadoPeriodo,
    EstadoPeriodoOperativo,
    EstadoRespuesta,
    OrigenEstadoPeriodo,
    TipoRespuesta,
)
from modules.usuarios.domain.models import Area


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def usuario_operador(db):
    """Create a test user for period operations."""
    User = get_user_model()
    return User.objects.create_user(
        username="operador_respuesta",
        email="operador_respuesta@cip.gob.pe",
        password="testpass123",
        dni="11223344",
        nombres="Carlos",
        apellidos="Ruiz",
    )


@pytest.fixture
def area_arquitectura(db):
    """Create a test area."""
    return Area.objects.create(
        nombre="Arquitectura",
        descripcion="Área de Arquitectura",
        activo=True,
    )


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_auth_client(user):
    """Create a ninja_extra TestClient with JWT auth for the given user."""
    client = TestClient(api)
    token = AccessToken.for_user(user)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = user
    return client


def _crear_solicitud_con_periodo_en_gestion(usuario, area):
    """
    Create a Solicitud in EN_GESTION state with one area assigned
    and a periodo in EN_GESTION state.
    Returns (solicitud, asignacion, periodo).
    """
    ahora = datetime.now()

    expediente = Expediente.objects.create(
        numero=200,
        tipo_persona="NATURAL",
        dni="55443322",
        nombres="Test",
        apellidos="Arquitecto",
        correo="test@example.com",
        telefono="900900900",
        tipo_documento="SOLICITUD",
        numero_documento="DOC-2026-F51-001",
        numero_folios=3,
        asunto="Solicitud para crear respuesta",
        fecha_registro=ahora,
        creado_por=usuario,
    )

    solicitud = Solicitud.objects.create(
        expediente=expediente,
        estado="EN_GESTION",
        prioridad="ALTA",
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

    asignacion = SolicitudAsignacion.objects.create(
        solicitud=solicitud,
        area=area,
        fecha_incorporacion=ahora,
        incorporado_por=usuario,
    )

    periodo = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        tipo_participacion="PRINCIPAL",
        estado=EstadoPeriodo.EN_GESTION,
        fecha_inicio=ahora,
        iniciado_por=usuario,
    )

    # Create initial historial record (PENDIENTE → EN_GESTION)
    SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
        periodo=periodo,
        estado_anterior=None,
        estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
        fecha_cambio=ahora,
        cambiado_por=usuario,
        origen=OrigenEstadoPeriodo.CREACION,
    )
    SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
        periodo=periodo,
        estado_anterior=EstadoPeriodoOperativo.PENDIENTE,
        estado_nuevo=EstadoPeriodoOperativo.EN_GESTION,
        fecha_cambio=ahora,
        cambiado_por=usuario,
        origen=OrigenEstadoPeriodo.AUTOASIGNACION,
    )

    return solicitud, asignacion, periodo


# ── Task 5.1: POST /periodos/{id}/respuestas — happy path ───────────────────

@pytest.mark.django_db
def test_crear_respuesta_borrador_en_gestion_happy_path(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionPeriodo in EN_GESTION state
    WHEN:  POST /periodos/{id}/respuestas is called with tipo_respuesta=INFORME
    THEN:  response status is 200
            AND respuesta.estado == BORRADOR
            AND respuesta.tipo_respuesta == INFORME
            AND respuesta.contenido is None (not provided)
            AND respuesta.emitido_por is None (draft)
            AND respuesta.fecha_emision is None (draft)
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "INFORME"},
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["estado"] == EstadoRespuesta.BORRADOR
    assert data["tipo_respuesta"] == "INFORME"
    assert data["contenido"] is None
    assert data["archivo"] is None
    assert data["fecha_emision"] is None
    assert data["emitido_por_id"] is None
    assert data["version"] == 1
    assert data["periodo_id"] == str(periodo.id)

    # Verify DB state
    respuesta = SolicitudAsignacionRespuesta.objects.get(id=data["id"])
    assert respuesta.estado == EstadoRespuesta.BORRADOR
    assert respuesta.tipo_respuesta == TipoRespuesta.INFORME
    assert respuesta.emitido_por is None
    assert respuesta.fecha_emision is None


@pytest.mark.django_db
def test_crear_respuesta_borrador_con_contenido_y_observacion(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionPeriodo in EN_GESTION state
    WHEN:  POST /periodos/{id}/respuestas is called with contenido and observacion
    THEN:  response status is 200
            AND respuesta.contenido matches the input
            AND respuesta.observacion matches the input
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    client = _make_auth_client(usuario_operador)
    payload = {
        "tipo_respuesta": "OBSERVACION",
        "contenido": "Se detectaron observaciones en el proyecto arquitectónico.",
        "observacion": "Revisar estructuralmente antes de aprobar.",
    }
    response = client.post(f"/periodos/{periodo.id}/respuestas", json=payload)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["estado"] == EstadoRespuesta.BORRADOR
    assert data["tipo_respuesta"] == "OBSERVACION"
    assert data["contenido"] == "Se detectaron observaciones en el proyecto arquitectónico."
    assert data["observacion"] == "Revisar estructuralmente antes de aprobar."


@pytest.mark.django_db
def test_crear_respuesta_borrador_en_periodo_pendiente(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionPeriodo in PENDIENTE state
    WHEN:  POST /periodos/{id}/respuestas is called
    THEN:  response status is 200
            AND respuesta.estado == BORRADOR (periodo PENDIENTE also accepts)
    """
    ahora = datetime.now()

    expediente = Expediente.objects.create(
        numero=300,
        tipo_persona="NATURAL",
        dni="66554433",
        nombres="Test",
        apellidos="Usuario",
        correo="test2@example.com",
        telefono="900900901",
        tipo_documento="SOLICITUD",
        numero_documento="DOC-2026-F51-002",
        numero_folios=1,
        asunto="Trámite en pendiente",
        fecha_registro=ahora,
        creado_por=usuario_operador,
    )

    solicitud = Solicitud.objects.create(
        expediente=expediente,
        estado="EN_GESTION",
        prioridad="MEDIA",
        fecha_registro=ahora,
        fecha_inicio_gestion=ahora,
        creado_por=usuario_operador,
    )
    SolicitudEstadoHistorial.objects.create(
        solicitud=solicitud,
        estado_anterior=None,
        estado_nuevo="REGISTRADA",
        cambiado_por=usuario_operador,
        fecha_cambio=ahora,
        origen="CREACION",
    )
    SolicitudEstadoHistorial.objects.create(
        solicitud=solicitud,
        estado_anterior="REGISTRADA",
        estado_nuevo="EN_GESTION",
        cambiado_por=usuario_operador,
        fecha_cambio=ahora,
        origen="CAMBIO_ESTADO",
    )

    asignacion = SolicitudAsignacion.objects.create(
        solicitud=solicitud,
        area=area_arquitectura,
        fecha_incorporacion=ahora,
        incorporado_por=usuario_operador,
    )

    periodo = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        tipo_participacion="PRINCIPAL",
        estado=EstadoPeriodo.PENDIENTE,
        fecha_inicio=ahora,
        iniciado_por=usuario_operador,
    )

    SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
        periodo=periodo,
        estado_anterior=None,
        estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
        fecha_cambio=ahora,
        cambiado_por=usuario_operador,
        origen=OrigenEstadoPeriodo.CREACION,
    )

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "CONFORMIDAD"},
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["estado"] == EstadoRespuesta.BORRADOR
    assert data["tipo_respuesta"] == "CONFORMIDAD"


@pytest.mark.django_db
def test_crear_respuesta_borrador_todos_los_tipos_validos(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionPeriodo in EN_GESTION state
    WHEN:  POST /periodos/{id}/respuestas is called with each valid tipo_respuesta
    THEN:  response status is 200 for all valid tipos
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    client = _make_auth_client(usuario_operador)

    for tipo in ["INFORME", "OBSERVACION", "CONFORMIDAD", "DESCARGO", "OTRO"]:
        response = client.post(
            f"/periodos/{periodo.id}/respuestas",
            json={"tipo_respuesta": tipo},
        )
        assert response.status_code == 200, (
            f"Expected 200 for tipo={tipo}, got {response.status_code}: {response.content}"
        )
        data = response.json()["data"]
        assert data["tipo_respuesta"] == tipo, f"tipo mismatch for {tipo}"
        assert data["estado"] == EstadoRespuesta.BORRADOR


# ── Task 5.1: Error paths ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_crear_respuesta_borrador_periodo_no_existe_devuelve_404(
    usuario_operador
):
    """
    GIVEN: a non-existent Periodo UUID
    WHEN:  POST /periodos/{id}/respuestas is called
    THEN:  response status is 404
    """
    from uuid import uuid4

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/periodos/{uuid4()}/respuestas",
        json={"tipo_respuesta": "INFORME"},
    )

    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_crear_respuesta_borrador_periodo_cerrado_devuelve_409(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionPeriodo in CERRADO state
    WHEN:  POST /periodos/{id}/respuestas is called
    THEN:  response status is 409
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    # Close the periodo first
    periodo.estado = EstadoPeriodo.CERRADO
    periodo.fecha_fin = datetime.now()
    periodo.save()

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "INFORME"},
    )

    assert response.status_code == 409, (
        f"Expected 409, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_crear_respuesta_borrador_tipo_invalido_devuelve_400(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a valid SolicitudAsignacionPeriodo in EN_GESTION
    WHEN:  POST /periodos/{id}/respuestas is called with invalid tipo_respuesta
    THEN:  response status is 400
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "INVALIDO"},
    )

    assert response.status_code == 400, (
        f"Expected 400, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_crear_respuesta_borrador_multiple_borradores_permitidos(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionPeriodo in EN_GESTION
    WHEN:  POST /periodos/{id}/respuestas is called multiple times
    THEN:  response status is 200 for each call
            AND multiple respuestas in BORRADOR exist for the same periodo
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    client = _make_auth_client(usuario_operador)

    # Create first draft
    response1 = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "INFORME", "contenido": "Primer borrador"},
    )
    assert response1.status_code == 200

    # Create second draft
    response2 = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "OBSERVACION", "contenido": "Segundo borrador"},
    )
    assert response2.status_code == 200

    # Verify both exist
    respuestas = SolicitudAsignacionRespuesta.objects.filter(
        periodo=periodo
    ).order_by("created_at")
    assert respuestas.count() == 2
    assert respuestas[0].tipo_respuesta == "INFORME"
    assert respuestas[1].tipo_respuesta == "OBSERVACION"


@pytest.mark.django_db
def test_crear_respuesta_borrador_sin_autenticacion_devuelve_401():
    """
    GIVEN: no authenticated user
    WHEN:  POST /periodos/{id}/respuestas is called
    THEN:  response status is 401 (unauthenticated)
    """
    client = TestClient(api)
    from uuid import uuid4

    response = client.post(
        f"/periodos/{uuid4()}/respuestas",
        json={"tipo_respuesta": "INFORME"},
    )

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )


# ── Task 5.2: GET /periodos/{id}/respuestas — list respuestas ──────────────


@pytest.mark.django_db
def test_listar_respuestas_varias_respuestas_happy_path(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionPeriodo in EN_GESTION with multiple respuestas
    WHEN:  GET /periodos/{id}/respuestas is called
    THEN:  response status is 200
            AND data is a list
            AND all respuestas for the periodo are returned
            AND each respuesta has correct fields
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    # Create two respuestas via API
    client = _make_auth_client(usuario_operador)

    resp1 = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "INFORME", "contenido": "Informe uno"},
    )
    assert resp1.status_code == 200

    resp2 = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "OBSERVACION", "contenido": "Observación dos"},
    )
    assert resp2.status_code == 200

    # Now GET the list
    response = client.get(f"/periodos/{periodo.id}/respuestas")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) == 2
    # Each item has the expected fields
    for item in data:
        assert "id" in item
        assert "periodo_id" in item
        assert "tipo_respuesta" in item
        assert "estado" in item
        assert "version" in item
        assert "created_at" in item


@pytest.mark.django_db
def test_listar_respuestas_vacio_sin_respuestas(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionPeriodo in EN_GESTION with no respuestas
    WHEN:  GET /periodos/{id}/respuestas is called
    THEN:  response status is 200
            AND data is an empty list
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    client = _make_auth_client(usuario_operador)
    response = client.get(f"/periodos/{periodo.id}/respuestas")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.django_db
def test_listar_respuestas_periodo_no_existe_devuelve_404(
    usuario_operador,
):
    """
    GIVEN: a non-existent Periodo UUID
    WHEN:  GET /periodos/{id}/respuestas is called
    THEN:  response status is 404
    """
    from uuid import uuid4

    client = _make_auth_client(usuario_operador)
    response = client.get(f"/periodos/{uuid4()}/respuestas")

    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_listar_respuestas_orden_descendente_por_created_at(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionPeriodo with multiple respuestas created at different times
    WHEN:  GET /periodos/{id}/respuestas is called
    THEN:  respuestas are ordered by created_at descending (newest first)
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    client = _make_auth_client(usuario_operador)

    # Create three respuestas
    for i, tipo in enumerate(["INFORME", "OBSERVACION", "CONFORMIDAD"]):
        resp = client.post(
            f"/periodos/{periodo.id}/respuestas",
            json={"tipo_respuesta": tipo, "contenido": f"Respuesta {i}"},
        )
        assert resp.status_code == 200

    # GET the list
    response = client.get(f"/periodos/{periodo.id}/respuestas")
    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data) == 3
    # Verify order: newest first (CONFORMIDAD created last, then OBSERVACION, then INFORME)
    assert data[0]["tipo_respuesta"] == "CONFORMIDAD"
    assert data[1]["tipo_respuesta"] == "OBSERVACION"
    assert data[2]["tipo_respuesta"] == "INFORME"


@pytest.mark.django_db
def test_listar_respuestas_sin_autenticacion_devuelve_401():
    """
    GIVEN: no authenticated user
    WHEN:  GET /periodos/{id}/respuestas is called
    THEN:  response status is 401 (unauthenticated)
    """
    client = TestClient(api)
    from uuid import uuid4

    response = client.get(f"/periodos/{uuid4()}/respuestas")

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_listar_respuestas_periodo_cerrado_retorna_lista_vacia(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionPeriodo in CERRADO state with no respuestas
    WHEN:  GET /periodos/{id}/respuestas is called
    THEN:  response status is 200
            AND data is an empty list (CERRADO periods can have zero respuestas)
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    # Close the periodo
    periodo.estado = EstadoPeriodo.CERRADO
    periodo.fecha_fin = datetime.now()
    periodo.save()

    client = _make_auth_client(usuario_operador)
    response = client.get(f"/periodos/{periodo.id}/respuestas")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) == 0


# ── Task 5.3: POST /respuestas/{id}/emitir — emitir respuesta ────────────────


@pytest.mark.django_db
def test_emitir_respuesta_borrador_happy_path(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionRespuesta in BORRADOR state
    WHEN:  POST /respuestas/{id}/emitir is called
    THEN:  response status is 200
            AND respuesta.estado == EMITIDA
            AND respuesta.fecha_emision is not None
            AND respuesta.emitido_por == usuario_operador
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    # First create a borrador respuesta
    client = _make_auth_client(usuario_operador)
    create_resp = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "INFORME", "contenido": "Informe técnico de arquitectura"},
    )
    assert create_resp.status_code == 200
    respuesta_id = create_resp.json()["data"]["id"]

    # Now emit it
    response = client.post(f"/respuestas/{respuesta_id}/emitir")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["estado"] == EstadoRespuesta.EMITIDA
    assert data["fecha_emision"] is not None
    assert data["emitido_por_id"] == str(usuario_operador.id)
    assert data["tipo_respuesta"] == "INFORME"
    assert data["contenido"] == "Informe técnico de arquitectura"

    # Verify DB state
    respuesta = SolicitudAsignacionRespuesta.objects.get(id=respuesta_id)
    assert respuesta.estado == EstadoRespuesta.EMITIDA
    assert respuesta.fecha_emision is not None
    assert respuesta.emitido_por_id == usuario_operador.id


@pytest.mark.django_db
def test_emitir_respuesta_ya_emitida_devuelve_400(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionRespuesta already in EMITIDA state
    WHEN:  POST /respuestas/{id}/emitir is called
    THEN:  response status is 400
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    # Create and emit a respuesta
    client = _make_auth_client(usuario_operador)
    create_resp = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "CONFORMIDAD"},
    )
    assert create_resp.status_code == 200
    respuesta_id = create_resp.json()["data"]["id"]

    # Emit first time
    emit1 = client.post(f"/respuestas/{respuesta_id}/emitir")
    assert emit1.status_code == 200

    # Try to emit again
    emit2 = client.post(f"/respuestas/{respuesta_id}/emitir")

    assert emit2.status_code == 400, (
        f"Expected 400, got {emit2.status_code}: {emit2.content}"
    )


@pytest.mark.django_db
def test_emitir_respuesta_no_existe_devuelve_404(
    usuario_operador,
):
    """
    GIVEN: a non-existent Respuesta UUID
    WHEN:  POST /respuestas/{id}/emitir is called
    THEN:  response status is 404
    """
    from uuid import uuid4

    client = _make_auth_client(usuario_operador)
    response = client.post(f"/respuestas/{uuid4()}/emitir")

    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_emitir_respuesta_periodo_cerrado_devuelve_409(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionRespuesta whose periodo is CERRADO
    WHEN:  POST /respuestas/{id}/emitir is called
    THEN:  response status is 409
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    # Create a borrador respuesta
    client = _make_auth_client(usuario_operador)
    create_resp = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "OBSERVACION"},
    )
    assert create_resp.status_code == 200
    respuesta_id = create_resp.json()["data"]["id"]

    # Close the periodo
    periodo.estado = EstadoPeriodo.CERRADO
    periodo.fecha_fin = datetime.now()
    periodo.save()

    # Try to emit
    response = client.post(f"/respuestas/{respuesta_id}/emitir")

    assert response.status_code == 409, (
        f"Expected 409, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_emitir_respuesta_sin_autenticacion_devuelve_401():
    """
    GIVEN: no authenticated user
    WHEN:  POST /respuestas/{id}/emitir is called
    THEN:  response status is 401
    """
    client = TestClient(api)
    from uuid import uuid4

    response = client.post(f"/respuestas/{uuid4()}/emitir")

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_emitir_respuesta_multiple_usuarios(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionRespuesta in BORRADOR
    WHEN:  a different user emits the respuesta
    THEN:  response status is 200
            AND respuesta.emitido_por is the second user
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    usuario_dos = User.objects.create_user(
        username="segundo_operador",
        email="segundo@cip.gob.pe",
        password="testpass123",
        dni="99887766",
        nombres="Ana",
        apellidos="López",
    )

    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    # Create borrador as primer usuario
    client1 = _make_auth_client(usuario_operador)
    create_resp = client1.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "INFORME"},
    )
    assert create_resp.status_code == 200
    respuesta_id = create_resp.json()["data"]["id"]

    # Emit as segundo usuario
    client2 = _make_auth_client(usuario_dos)
    response = client2.post(f"/respuestas/{respuesta_id}/emitir")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["estado"] == EstadoRespuesta.EMITIDA
    assert data["emitido_por_id"] == str(usuario_dos.id)

    # Verify DB
    respuesta = SolicitudAsignacionRespuesta.objects.get(id=respuesta_id)
    assert respuesta.emitido_por_id == usuario_dos.id


# ── Task 5.4: POST /respuestas/{id}/anular — anular respuesta ────────────────


@pytest.mark.django_db
def test_anular_respuesta_emitida_happy_path(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionRespuesta in EMITIDA state
    WHEN:  POST /respuestas/{id}/anular is called
    THEN:  response status is 200
            AND respuesta.estado == ANULADA
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    # First create and emit a respuesta
    client = _make_auth_client(usuario_operador)
    create_resp = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "INFORME", "contenido": "Informe técnico"},
    )
    assert create_resp.status_code == 200
    respuesta_id = create_resp.json()["data"]["id"]

    # Emit the respuesta first
    emit_resp = client.post(f"/respuestas/{respuesta_id}/emitir")
    assert emit_resp.status_code == 200
    assert emit_resp.json()["data"]["estado"] == EstadoRespuesta.EMITIDA

    # Now annul it
    response = client.post(f"/respuestas/{respuesta_id}/anular")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["estado"] == EstadoRespuesta.ANULADA
    assert data["tipo_respuesta"] == "INFORME"
    assert data["contenido"] == "Informe técnico"

    # Verify DB state
    respuesta = SolicitudAsignacionRespuesta.objects.get(id=respuesta_id)
    assert respuesta.estado == EstadoRespuesta.ANULADA


@pytest.mark.django_db
def test_anular_respuesta_ya_anulada_devuelve_400(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionRespuesta already in ANULADA state
    WHEN:  POST /respuestas/{id}/anular is called
    THEN:  response status is 400
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    # Create, emit, and annul a respuesta
    client = _make_auth_client(usuario_operador)
    create_resp = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "OBSERVACION"},
    )
    assert create_resp.status_code == 200
    respuesta_id = create_resp.json()["data"]["id"]

    # Emit first
    client.post(f"/respuestas/{respuesta_id}/emitir")
    # Then annul
    client.post(f"/respuestas/{respuesta_id}/anular")

    # Try to annul again
    response2 = client.post(f"/respuestas/{respuesta_id}/anular")

    assert response2.status_code == 400, (
        f"Expected 400, got {response2.status_code}: {response2.content}"
    )


@pytest.mark.django_db
def test_anular_respuesta_no_existe_devuelve_404(
    usuario_operador,
):
    """
    GIVEN: a non-existent Respuesta UUID
    WHEN:  POST /respuestas/{id}/anular is called
    THEN:  response status is 404
    """
    client = _make_auth_client(usuario_operador)
    from uuid import uuid4

    response = client.post(f"/respuestas/{uuid4()}/anular")

    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_anular_respuesta_borrador_devuelve_400(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionRespuesta in BORRADOR state (not yet emitted)
    WHEN:  POST /respuestas/{id}/anular is called
    THEN:  response status is 400
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    # Create a borrador (don't emit it)
    client = _make_auth_client(usuario_operador)
    create_resp = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "INFORME"},
    )
    assert create_resp.status_code == 200
    respuesta_id = create_resp.json()["data"]["id"]

    # Try to annul a borrador
    response = client.post(f"/respuestas/{respuesta_id}/anular")

    assert response.status_code == 400, (
        f"Expected 400, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_anular_respuesta_sin_autenticacion_devuelve_401():
    """
    GIVEN: no authenticated user
    WHEN:  POST /respuestas/{id}/anular is called
    THEN:  response status is 401
    """
    client = TestClient(api)
    from uuid import uuid4

    response = client.post(f"/respuestas/{uuid4()}/anular")

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )


# ── Task 5.5: POST /respuestas/{id}/rectificar — rectificar respuesta ────────


@pytest.mark.django_db
def test_rectificar_respuesta_emitida_happy_path(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionRespuesta in EMITIDA state
    WHEN:  POST /respuestas/{id}/rectificar is called
    THEN:  response status is 200
            AND respuesta.estado == RECTIFICADA
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    # First create and emit a respuesta
    client = _make_auth_client(usuario_operador)
    create_resp = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "INFORME", "contenido": "Informe técnico"},
    )
    assert create_resp.status_code == 200
    respuesta_id = create_resp.json()["data"]["id"]

    # Emit the respuesta first
    emit_resp = client.post(f"/respuestas/{respuesta_id}/emitir")
    assert emit_resp.status_code == 200
    assert emit_resp.json()["data"]["estado"] == EstadoRespuesta.EMITIDA

    # Now rectify it
    response = client.post(f"/respuestas/{respuesta_id}/rectificar")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["estado"] == EstadoRespuesta.RECTIFICADA
    assert data["tipo_respuesta"] == "INFORME"
    assert data["contenido"] == "Informe técnico"

    # Verify DB state
    respuesta = SolicitudAsignacionRespuesta.objects.get(id=respuesta_id)
    assert respuesta.estado == EstadoRespuesta.RECTIFICADA


@pytest.mark.django_db
def test_rectificar_respuesta_ya_rectificada_devuelve_400(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionRespuesta already in RECTIFICADA state
    WHEN:  POST /respuestas/{id}/rectificar is called
    THEN:  response status is 400
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    client = _make_auth_client(usuario_operador)
    create_resp = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "OBSERVACION"},
    )
    assert create_resp.status_code == 200
    respuesta_id = create_resp.json()["data"]["id"]

    # Emit first
    client.post(f"/respuestas/{respuesta_id}/emitir")
    # Then rectify
    client.post(f"/respuestas/{respuesta_id}/rectificar")

    # Try to rectify again
    response2 = client.post(f"/respuestas/{respuesta_id}/rectificar")

    assert response2.status_code == 400, (
        f"Expected 400, got {response2.status_code}: {response2.content}"
    )


@pytest.mark.django_db
def test_rectificar_respuesta_no_existe_devuelve_404(
    usuario_operador,
):
    """
    GIVEN: a non-existent Respuesta UUID
    WHEN:  POST /respuestas/{id}/rectificar is called
    THEN:  response status is 404
    """
    client = _make_auth_client(usuario_operador)
    from uuid import uuid4

    response = client.post(f"/respuestas/{uuid4()}/rectificar")

    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_rectificar_respuesta_borrador_devuelve_400(
    usuario_operador, area_arquitectura
):
    """
    GIVEN: a SolicitudAsignacionRespuesta in BORRADOR state (not yet emitted)
    WHEN:  POST /respuestas/{id}/rectificar is called
    THEN:  response status is 400
    """
    _, _, periodo = _crear_solicitud_con_periodo_en_gestion(
        usuario_operador, area_arquitectura
    )

    # Create a borrador (don't emit it)
    client = _make_auth_client(usuario_operador)
    create_resp = client.post(
        f"/periodos/{periodo.id}/respuestas",
        json={"tipo_respuesta": "INFORME"},
    )
    assert create_resp.status_code == 200
    respuesta_id = create_resp.json()["data"]["id"]

    # Try to rectify a borrador
    response = client.post(f"/respuestas/{respuesta_id}/rectificar")

    assert response.status_code == 400, (
        f"Expected 400, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_rectificar_respuesta_sin_autenticacion_devuelve_401():
    """
    GIVEN: no authenticated user
    WHEN:  POST /respuestas/{id}/rectificar is called
    THEN:  response status is 401
    """
    client = TestClient(api)
    from uuid import uuid4

    response = client.post(f"/respuestas/{uuid4()}/rectificar")

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )
