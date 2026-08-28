"""
E2E tests for Participacion Fase 4.5 — Retirar participación de usuario.

Tests cover:
- 4.5: POST /participaciones-usuario/{id}/retirar — retirar a un usuario de una participación activa

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
    SolicitudAsignacionUsuario,
)
from modules.asignaciones.domain.constants import (
    EstadoPeriodo,
    EstadoPeriodoOperativo,
    OrigenEstadoPeriodo,
)
from modules.usuarios.domain.models import Area


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def usuario_operador(db):
    """Create a test user for period operations."""
    User = get_user_model()
    return User.objects.create_user(
        username="operador_participacion",
        email="operador_participacion@cip.gob.pe",
        password="testpass123",
        dni="99887755",
        nombres="Elena",
        apellidos="Rojas",
    )


@pytest.fixture
def area_gestion(db):
    """Create a test area."""
    return Area.objects.create(
        nombre="Gestión Participacion",
        descripcion="Área de Gestión",
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


def _crear_solicitud_con_periodo_y_participacion(usuario, area):
    """
    Create a Solicitud in EN_GESTION state with one area assigned,
    a periodo in EN_GESTION state, and one active user participation.
    Returns (solicitud, asignacion, periodo, participacion).
    """
    ahora = datetime.now()

    expediente = Expediente.objects.create(
        numero=101,
        tipo_persona="NATURAL",
        dni="55443311",
        nombres="Test",
        apellidos="User",
        correo="test2@example.com",
        telefono="900900901",
        tipo_documento="SOLICITUD",
        numero_documento="DOC-2026-P45-001",
        numero_folios=2,
        asunto="Trámite para probar retiro de participación",
        fecha_registro=ahora,
        creado_por=usuario,
    )

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

    # Active participation
    participacion = SolicitudAsignacionUsuario.objects.create(
        periodo=periodo,
        usuario=usuario,
        rol="Responsable",
        fecha_inicio=ahora,
        asignado_por=usuario,
    )

    return solicitud, asignacion, periodo, participacion


# ── Task 4.5: POST /participaciones-usuario/{id}/retirar — happy path ─────────

@pytest.mark.django_db
def test_retirar_participacion_activa_marca_fecha_fin(
    usuario_operador, area_gestion
):
    """
    GIVEN: an active SolicitudAsignacionUsuario (fecha_fin is NULL)
           linked to a periodo in EN_GESTION state
    WHEN:  POST /participaciones-usuario/{id}/retirar is called
    THEN:  response status is 200
            AND participacion.fecha_fin is set
            AND participacion.retirado_por == usuario_operador
            AND response includes the parent solicitud data
    """
    _, _, _, participacion = _crear_solicitud_con_periodo_y_participacion(
        usuario_operador, area_gestion
    )

    client = _make_auth_client(usuario_operador)
    response = client.post(f"/participaciones-usuario/{participacion.id}/retirar")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["id"] == str(participacion.periodo.asignacion.solicitud.id)
    assert data["estado"] == "EN_GESTION"

    # Verify DB state: participation is marked as finished
    participacion.refresh_from_db()
    assert participacion.fecha_fin is not None, (
        "Participacion should have fecha_fin set"
    )
    assert participacion.retirado_por == usuario_operador, (
        "Participacion.retirado_por should be the authenticated user"
    )


@pytest.mark.django_db
def test_retirar_participacion_con_motivo_guarda_motivo(
    usuario_operador, area_gestion
):
    """
    GIVEN: an active SolicitudAsignacionUsuario linked to a periodo in EN_GESTION
    WHEN:  POST /participaciones-usuario/{id}/retirar is called with a motivo
    THEN:  response status is 200
            AND participacion.motivo_retiro == the provided motivo
    """
    _, _, _, participacion = _crear_solicitud_con_periodo_y_participacion(
        usuario_operador, area_gestion
    )

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/participaciones-usuario/{participacion.id}/retirar",
        json={"motivo": "El usuario fue reasignado a otro trámite urgente"},
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    participacion.refresh_from_db()
    assert participacion.motivo_retiro == "El usuario fue reasignado a otro trámite urgente"


@pytest.mark.django_db
def test_retirar_participacion_respuesta_incluye_solicitud(
    usuario_operador, area_gestion
):
    """
    GIVEN: an active SolicitudAsignacionUsuario
    WHEN:  POST /participaciones-usuario/{id}/retirar is called
    THEN:  response includes the parent solicitud data with expediente and asignaciones
    """
    _, _, _, participacion = _crear_solicitud_con_periodo_y_participacion(
        usuario_operador, area_gestion
    )

    client = _make_auth_client(usuario_operador)
    response = client.post(f"/participaciones-usuario/{participacion.id}/retirar")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert "expediente" in data
    assert "asignaciones" in data
    assert len(data["asignaciones"]) == 1
    asig = data["asignaciones"][0]
    assert asig["area_id"] == str(area_gestion.id)
    assert asig["area_nombre"] == area_gestion.nombre


# ── Task 4.5: Error paths ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_retirar_participacion_no_existe_devuelve_404(usuario_operador):
    """
    GIVEN: a non-existent Participacion UUID
    WHEN:  POST /participaciones-usuario/{id}/retirar is called
    THEN:  response status is 404
    """
    from uuid import uuid4

    client = _make_auth_client(usuario_operador)
    response = client.post(f"/participaciones-usuario/{uuid4()}/retirar")

    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_retirar_participacion_ya_retirada_devuelve_409(
    usuario_operador, area_gestion
):
    """
    GIVEN: an inactive SolicitudAsignacionUsuario (fecha_fin is already set)
    WHEN:  POST /participaciones-usuario/{id}/retirar is called
    THEN:  response status is 409
    """
    _, _, _, participacion = _crear_solicitud_con_periodo_y_participacion(
        usuario_operador, area_gestion
    )

    # Manually mark as retired
    participacion.fecha_fin = datetime.now()
    participacion.retirado_por = usuario_operador
    participacion.motivo_retiro = "Retiro previo"
    participacion.save()

    client = _make_auth_client(usuario_operador)
    response = client.post(f"/participaciones-usuario/{participacion.id}/retirar")

    assert response.status_code == 409, (
        f"Expected 409, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_retirar_participacion_periodo_cerrado_devuelve_409(
    usuario_operador, area_gestion
):
    """
    GIVEN: an active SolicitudAsignacionUsuario linked to a periodo in CERRADO state
    WHEN:  POST /participaciones-usuario/{id}/retirar is called
    THEN:  response status is 409
    """
    _, _, _, participacion = _crear_solicitud_con_periodo_y_participacion(
        usuario_operador, area_gestion
    )

    # Close the periodo
    participacion.periodo.estado = EstadoPeriodo.CERRADO
    participacion.periodo.save()

    client = _make_auth_client(usuario_operador)
    response = client.post(f"/participaciones-usuario/{participacion.id}/retirar")

    assert response.status_code == 409, (
        f"Expected 409, got {response.status_code}: {response.content}"
    )
