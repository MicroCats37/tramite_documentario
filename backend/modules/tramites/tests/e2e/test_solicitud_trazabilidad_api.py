"""
E2E tests for GET /solicitudes/{solicitud_id}/trazabilidad

Covers auth, not-found, and top-level response contract.
Nested graph correctness and query budget are verified in the
integration test suite (test_solicitud_trazabilidad.py).

Uses ninja_extra.testing.TestClient (sync) per TEST_ARCHITECTURE_CONTRACT.
"""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from django.contrib.auth import get_user_model
from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api

from modules.tramites.domain.models import Expediente, Solicitud, TipoDocumento
from modules.tramites.domain.constants import EstadoSolicitud
from modules.asignaciones.domain.models import SolicitudAsignacion
from modules.asignaciones.domain.constants import TipoParticipacion, EstadoPeriodo
from modules.usuarios.domain.models import Area
from modules.tramites.domain.models.solicitud_historial import SolicitudEstadoHistorial


pytestmark = pytest.mark.django_db


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user(username, dni, nombres, apellidos):
    User = get_user_model()
    return User.objects.create_user(
        username=username, email=f"{username}@cip.gob.pe", password="testpass123",
        dni=dni, nombres=nombres, apellidos=apellidos,
    )


def _auth_client(user):
    """Return a TestClient authenticated as user."""
    client = TestClient(api)
    client.headers.update({"Authorization": f"Bearer {AccessToken.for_user(user)}"})
    return client


def _build_solicitud_con_trazabilidad(user, estado=EstadoSolicitud.EN_GESTION):
    """Minimal solicitud with a global historial entry (required for non-empty timeline)."""
    tipo_doc = TipoDocumento.objects.get(nombre="SOLICITUD")
    exp = Expediente.objects.create(
        numero=999, tipo_persona="NATURAL", dni="12345678",
        nombres="Test", apellidos="User", correo="test@test.com",
        telefono="999888777", tipo_documento=tipo_doc,
        numero_documento="DOC-9999", numero_folios=5,
        asunto="Trámite E2E trazabilidad", fecha_registro=datetime.now(timezone.utc),
        creado_por=user,
    )
    sol = Solicitud.objects.create(
        expediente=exp, estado=estado, prioridad="MEDIA",
        fecha_registro=datetime.now(timezone.utc), creado_por=user,
    )
    SolicitudEstadoHistorial.objects.create(
        solicitud=sol, estado_anterior=None, estado_nuevo=estado,
        fecha_cambio=datetime.now(timezone.utc), cambiado_por=user, origen="CREACION",
    )
    return sol


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestTrazabilidadAuth:
    """Auth: unauthenticated requests are rejected."""

    def test_sin_token_retorna_401(self):
        """Unauthenticated GET returns 401."""
        client = TestClient(api)
        response = client.get(f"/solicitudes/{uuid4()}/trazabilidad")
        assert response.status_code == 401

    def test_token_invalido_retorna_401(self):
        """Invalid Bearer token returns 401."""
        client = TestClient(api)
        client.headers.update({"Authorization": "Bearer invalid-token"})
        response = client.get(f"/solicitudes/{uuid4()}/trazabilidad")
        assert response.status_code == 401


class TestTrazabilidadNotFound:
    """404 for nonexistent solicitud."""

    def test_uuid_inexistente_retorna_404(self):
        """Nonexistent UUID returns 404."""
        user = _make_user("e2e_notfound", "11111111", "Not", "Found")
        resp = _auth_client(user).get(f"/solicitudes/{uuid4()}/trazabilidad")
        assert resp.status_code == 404


class TestTrazabilidadWrapperContract:
    """Top-level response wrapper and root fields."""

    def test_retorna_wrapper_con_data(self):
        """Response is wrapped in standard ApiResponse {data: {...}}."""
        user = _make_user("e2e_wrapper", "22222222", "Wrapper", "User")
        sol = _build_solicitud_con_trazabilidad(user)

        resp = _auth_client(user).get(f"/solicitudes/{sol.id}/trazabilidad")
        assert resp.status_code == 200

        payload = resp.json()
        assert "data" in payload, f"Expected 'data' key in response: {payload}"

    def test_root_tiene_solo_campos_requeridos(self):
        """
        Root object contains only: solicitud_id, areas, historial_estados, timeline.
        No extra fields (no directamente-nivel raiz como 'periodos').
        """
        user = _make_user("e2e_root", "33333333", "Root", "User")
        sol = _build_solicitud_con_trazabilidad(user)

        resp = _auth_client(user).get(f"/solicitudes/{sol.id}/trazabilidad")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert set(data.keys()) == {"solicitud_id", "areas", "historial_estados", "timeline"}

    def test_solicitud_id_coincide_con_solicitud(self):
        """Root solicitud_id matches the requested solicitud UUID."""
        user = _make_user("e2e_solmatch", "44444444", "Sol", "Match")
        sol = _build_solicitud_con_trazabilidad(user)

        resp = _auth_client(user).get(f"/solicitudes/{sol.id}/trazabilidad")
        assert resp.status_code == 200

        data = resp.json()["data"]
        assert data["solicitud_id"] == str(sol.id)


class TestTrazabilidadNestedContract:
    """Nested structure: areas contain etapas (not periods)."""

    def test_area_contiene_etapas_no_periodos(self):
        """
        Each area object contains 'etapas' (not 'periodos').
        Etapas contain participants nested directly (not at assignment level).
        """
        user = _make_user("e2e_nested", "55555555", "Nested", "User")
        sol = _build_solicitud_con_trazabilidad(user)
        base = datetime.now(timezone.utc)

        area = Area.objects.create(nombre="Área E2E", activo=True)
        asig = SolicitudAsignacion.objects.create(
            solicitud=sol, area=area, fecha_incorporacion=base - timedelta(hours=1),
            incorporado_por=user,
        )
        from modules.asignaciones.domain.models import SolicitudAsignacionPeriodo
        SolicitudAsignacionPeriodo.objects.create(
            asignacion=asig, numero_ciclo=1, tipo_participacion=TipoParticipacion.PRINCIPAL,
            estado=EstadoPeriodo.EN_GESTION, fecha_inicio=base - timedelta(hours=1),
            iniciado_por=user,
        )

        resp = _auth_client(user).get(f"/solicitudes/{sol.id}/trazabilidad")
        assert resp.status_code == 200

        areas = resp.json()["data"]["areas"]
        assert len(areas) == 1
        assert "etapas" in areas[0], f"Expected 'etapas' in area, got: {list(areas[0].keys())}"
        assert "periodos" not in areas[0]
