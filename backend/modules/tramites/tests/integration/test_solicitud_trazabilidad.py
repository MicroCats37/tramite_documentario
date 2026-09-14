"""
Integration tests for GET /solicitudes/{solicitud_id}/trazabilidad

Covers: empty graph, nested periods/participants/responses, audit fields,
deterministic timeline ordering, bounded query cardinality.
"""
import pytest
from datetime import datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api

from modules.tramites.domain.models import Expediente, Solicitud, TipoDocumento
from modules.tramites.domain.constants import EstadoSolicitud
from modules.asignaciones.domain.models import (
    SolicitudAsignacion, SolicitudAsignacionPeriodo,
    SolicitudAsignacionUsuario, SolicitudAsignacionRespuesta,
    SolicitudAsignacionPeriodoEstadoHistorial,
)
from modules.asignaciones.domain.constants import (
    EstadoPeriodo, TipoParticipacion, EstadoPeriodoOperativo,
    OrigenEstadoPeriodo, TipoRespuesta, EstadoRespuesta,
)
from modules.usuarios.domain.models import Area
from modules.tramites.domain.models.solicitud_historial import SolicitudEstadoHistorial


pytestmark = pytest.mark.django_db


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_user(username, dni, nombres, apellidos):
    User = get_user_model()
    return User.objects.create_user(
        username=username, email=f"{username}@cip.gob.pe", password="testpass123",
        dni=dni, nombres=nombres, apellidos=apellidos,
    )


def _make_exp(numero, user, tipo_doc):
    return Expediente.objects.create(
        numero=numero, tipo_persona="NATURAL", dni="12345678",
        nombres="Test", apellidos="User", correo="test@test.com",
        telefono="999888777", tipo_documento=tipo_doc,
        numero_documento=f"DOC-{numero:04d}", numero_folios=5,
        asunto=f"Trámite {numero}", fecha_registro=datetime.now(timezone.utc),
        creado_por=user,
    )


def _make_solicitud(exp, user, estado=EstadoSolicitud.REGISTRADA):
    return Solicitud.objects.create(
        expediente=exp, estado=estado, prioridad="MEDIA",
        fecha_registro=datetime.now(timezone.utc), creado_por=user,
    )


def _add_historial_solicitud(solicitud, anterior, nuevo, user, fecha, origen="CAMBIO_ESTADO"):
    SolicitudEstadoHistorial.objects.create(
        solicitud=solicitud, estado_anterior=anterior, estado_nuevo=nuevo,
        fecha_cambio=fecha, cambiado_por=user, origen=origen,
    )


def _add_periodo(asignacion, ciclo, tipo_part, user, inicio, estado, fin=None):
    p = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion, numero_ciclo=ciclo, tipo_participacion=tipo_part,
        estado=estado, fecha_inicio=inicio, fecha_fin=fin, iniciado_por=user,
    )
    SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
        periodo=p, estado_anterior=None, estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
        fecha_cambio=inicio, cambiado_por=user, origen=OrigenEstadoPeriodo.CREACION,
    )
    return p


def _add_participante(periodo, usuario, rol, user, inicio, fin=None):
    SolicitudAsignacionUsuario.objects.create(
        periodo=periodo, usuario=usuario, rol=rol,
        fecha_inicio=inicio, fecha_fin=fin,
        asignado_por=user, retirado_por=user if fin else None,
        motivo_retiro="Retiro por derivación" if fin else None,
    )


def _add_respuesta(periodo, tipo, estado, user, emision):
    SolicitudAsignacionRespuesta.objects.create(
        periodo=periodo, tipo_respuesta=tipo, estado=estado,
        fecha_emision=emision, emitido_por=user, contenido="Test",
    )


def _add_historial_periodo(periodo, anterior, nuevo, user, fecha, origen):
    SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
        periodo=periodo, estado_anterior=anterior, estado_nuevo=nuevo,
        fecha_cambio=fecha, cambiado_por=user, origen=origen,
    )


def _auth_client(user):
    client = TestClient(api)
    client.headers.update({"Authorization": f"Bearer {AccessToken.for_user(user)}"})
    client.user = user
    return client


# ── Tests ────────────────────────────────────────────────────────────────────────

class TestTrazabilidadEmpty:
    """Empty/minimal graph and 404."""

    def test_sin_asignaciones_retorna_estructura_vacia(self, db):
        """Solicitud sin asignaciones retorna areas vacias pero con historial y timeline."""
        user = _make_user("u1", "11111111", "One", "User")
        tipo_doc = TipoDocumento.objects.get(nombre="SOLICITUD")
        exp = _make_exp(1, user, tipo_doc)
        sol = _make_solicitud(exp, user)
        _add_historial_solicitud(sol, None, EstadoSolicitud.REGISTRADA, user, datetime.now(timezone.utc), "CREACION")

        resp = _auth_client(user).get(f"/solicitudes/{sol.id}/trazabilidad")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["solicitud_id"] == str(sol.id)
        assert data["areas"] == []
        assert len(data["historial_estados"]) >= 1
        assert len(data["timeline"]) >= 1

    def test_no_existente_retorna_404(self, db):
        """UUID inexistente retorna 404."""
        from uuid import uuid4
        user = _make_user("u2", "22222222", "Two", "User")
        resp = _auth_client(user).get(f"/solicitudes/{uuid4()}/trazabilidad")
        assert resp.status_code == 404


class TestTrazabilidadNestedGraph:
    """Full nested graph: areas, periods, participants, responses, audit fields."""

    def test_grafo_completo_estructura_correcta(self, db):
        """
        GIVEN: 2 areas, multiple periods, active+retired participants,
                responses, period state history
        WHEN:  GET /solicitudes/{id}/trazabilidad
        THEN:  Nested structure correct, audit fields populated, Principal→Adjunta progression
        """
        user = _make_user("admin", "33333333", "Admin", "User")
        user2 = _make_user("user2", "44444444", "Two", "User")
        tipo_doc = TipoDocumento.objects.get(nombre="SOLICITUD")
        exp = _make_exp(2, user, tipo_doc)
        sol = _make_solicitud(exp, user)
        base = datetime.now(timezone.utc)

        # Global history
        _add_historial_solicitud(sol, None, EstadoSolicitud.REGISTRADA, user, base - timedelta(hours=5), "CREACION")
        _add_historial_solicitud(sol, EstadoSolicitud.REGISTRADA, EstadoSolicitud.EN_GESTION, user, base - timedelta(hours=4))

        # Area 1: Arquitectura — two periods (PRINCIPAL closed, ADJUNTA active)
        area1 = Area.objects.create(nombre="Arquitectura", activo=True)
        asig1 = SolicitudAsignacion.objects.create(
            solicitud=sol, area=area1, fecha_incorporacion=base - timedelta(hours=4), incorporado_por=user,
        )
        p1 = _add_periodo(asig1, 1, TipoParticipacion.PRINCIPAL, user, base - timedelta(hours=4), EstadoPeriodo.CERRADO, base - timedelta(minutes=35))
        _add_historial_periodo(p1, EstadoPeriodoOperativo.PENDIENTE, EstadoPeriodoOperativo.EN_GESTION, user, base - timedelta(hours=3), OrigenEstadoPeriodo.AUTOASIGNACION)
        _add_historial_periodo(p1, EstadoPeriodoOperativo.EN_GESTION, EstadoPeriodoOperativo.CERRADO, user, base - timedelta(minutes=35), OrigenEstadoPeriodo.CIERRE)
        _add_participante(p1, user, "Responsable", user, base - timedelta(hours=4))
        _add_respuesta(p1, TipoRespuesta.INFORME, EstadoRespuesta.EMITIDA, user, base - timedelta(hours=1))

        p2 = _add_periodo(asig1, 2, TipoParticipacion.ADJUNTA, user, base - timedelta(minutes=30), EstadoPeriodo.EN_GESTION)
        _add_participante(p2, user2, "Revisor", user, base - timedelta(minutes=30))
        _add_respuesta(p2, TipoRespuesta.OBSERVACION, EstadoRespuesta.EMITIDA, user, base - timedelta(minutes=15))

        # Area 2: Estructuras — one period with active + retired participant
        area2 = Area.objects.create(nombre="Estructuras", activo=True)
        asig2 = SolicitudAsignacion.objects.create(
            solicitud=sol, area=area2, fecha_incorporacion=base - timedelta(hours=3), incorporado_por=user,
        )
        p3 = _add_periodo(asig2, 1, TipoParticipacion.PRINCIPAL, user, base - timedelta(hours=3), EstadoPeriodo.CERRADO, base - timedelta(hours=1))
        _add_participante(p3, user, "Responsable", user, base - timedelta(hours=3))
        _add_participante(p3, user2, "Colaborador", user, base - timedelta(hours=3), base - timedelta(hours=1))
        _add_respuesta(p3, TipoRespuesta.CONFORMIDAD, EstadoRespuesta.EMITIDA, user, base - timedelta(hours=1))

        resp = _auth_client(user).get(f"/solicitudes/{sol.id}/trazabilidad")

        assert resp.status_code == 200
        data = resp.json()["data"]

        # Root checks
        assert len(data["areas"]) == 2
        assert len(data["historial_estados"]) == 2
        assert len(data["timeline"]) > 0

        # Arquitectura: PRINCIPAL → ADJUNTA
        arq = next(a for a in data["areas"] if a["area_nombre"] == "Arquitectura")
        assert arq["etapas"][0]["tipo_participacion"] == "PRINCIPAL"
        assert arq["etapas"][0]["estado"] == "CERRADO"
        assert arq["etapas"][1]["tipo_participacion"] == "ADJUNTA"
        assert arq["etapas"][1]["estado"] == "EN_GESTION"

        # Period 1: 3 historial states (initial + 2 transitions)
        assert len(arq["etapas"][0]["historial_estados"]) == 3
        assert arq["etapas"][0]["participantes"][0]["activo"] is True
        assert arq["etapas"][0]["respuestas"][0]["tipo_respuesta"] == "INFORME"

        # Estructuras: active + retired participant
        est = next(a for a in data["areas"] if a["area_nombre"] == "Estructuras")
        partes = est["etapas"][0]["participantes"]
        assert len(partes) == 2
        assert partes[0]["activo"] is True
        assert partes[1]["activo"] is False
        assert partes[1]["retirado_por_id"] is not None
        assert partes[1]["motivo_retiro"] is not None

    def test_audit_fields_correctly_populated(self, db):
        """Participant audit fields (asignado_por, retirado_por) are correctly populated."""
        user = _make_user("admin3", "55555555", "Admin3", "User")
        user_ret = _make_user("retirado", "66666666", "Ret", "User")
        tipo_doc = TipoDocumento.objects.get(nombre="SOLICITUD")
        exp = _make_exp(3, user, tipo_doc)
        sol = _make_solicitud(exp, user)
        base = datetime.now(timezone.utc)

        area = Area.objects.create(nombre="Área Audit", activo=True)
        asig = SolicitudAsignacion.objects.create(
            solicitud=sol, area=area, fecha_incorporacion=base - timedelta(hours=2), incorporado_por=user,
        )
        p = _add_periodo(asig, 1, TipoParticipacion.PRINCIPAL, user, base - timedelta(hours=2), EstadoPeriodo.CERRADO, base - timedelta(hours=1))
        _add_participante(p, user, "Responsable", user, base - timedelta(hours=2))
        _add_participante(p, user_ret, "Colaborador", user, base - timedelta(hours=2), base - timedelta(hours=1))

        resp = _auth_client(user).get(f"/solicitudes/{sol.id}/trazabilidad")
        assert resp.status_code == 200

        partes = resp.json()["data"]["areas"][0]["etapas"][0]["participantes"]
        activo = next(p for p in partes if p["activo"])
        retired = next(p for p in partes if not p["activo"])

        assert activo["asignado_por_id"] is not None
        assert activo["asignado_por_nombres"] is not None
        assert activo["retirado_por_id"] is None
        assert retired["asignado_por_id"] is not None
        assert retired["retirado_por_id"] is not None
        assert retired["retirado_por_nombres"] is not None
        assert retired["motivo_retiro"] is not None


class TestTrazabilidadTimeline:
    """Timeline ordering and determinism."""

    def test_timeline_orden_cronologico_ascendente(self, db):
        """Timeline events are sorted chronologically (ascending)."""
        user = _make_user("admin4", "77777777", "Admin4", "User")
        tipo_doc = TipoDocumento.objects.get(nombre="SOLICITUD")
        exp = _make_exp(4, user, tipo_doc)
        sol = _make_solicitud(exp, user)
        base = datetime.now(timezone.utc)

        _add_historial_solicitud(sol, None, EstadoSolicitud.REGISTRADA, user, base - timedelta(hours=5))
        area = Area.objects.create(nombre="Área T", activo=True)
        asig = SolicitudAsignacion.objects.create(solicitud=sol, area=area, fecha_incorporacion=base - timedelta(hours=4), incorporado_por=user)
        p = _add_periodo(asig, 1, TipoParticipacion.PRINCIPAL, user, base - timedelta(hours=4), EstadoPeriodo.CERRADO, base - timedelta(hours=1))
        _add_participante(p, user, "Responsable", user, base - timedelta(hours=3))
        _add_respuesta(p, TipoRespuesta.INFORME, EstadoRespuesta.EMITIDA, user, base - timedelta(hours=1))

        resp = _auth_client(user).get(f"/solicitudes/{sol.id}/trazabilidad")
        assert resp.status_code == 200

        tl = resp.json()["data"]["timeline"]
        timestamps = [e["timestamp"] for e in tl]
        assert timestamps == sorted(timestamps)

    def test_timeline_tiebreaker_deterministic(self, db):
        """Same-timestamp events are ordered deterministically by tipo + descripcion."""
        user = _make_user("admin5", "88888888", "Admin5", "User")
        tipo_doc = TipoDocumento.objects.get(nombre="SOLICITUD")
        exp = _make_exp(5, user, tipo_doc)
        sol = _make_solicitud(exp, user)
        base = datetime.now(timezone.utc)

        _add_historial_solicitud(sol, None, EstadoSolicitud.REGISTRADA, user, base, "CREACION")
        area_a = Area.objects.create(nombre="Área A", activo=True)
        area_b = Area.objects.create(nombre="Área B", activo=True)
        SolicitudAsignacion.objects.create(solicitud=sol, area=area_a, fecha_incorporacion=base, incorporado_por=user)
        SolicitudAsignacion.objects.create(solicitud=sol, area=area_b, fecha_incorporacion=base, incorporado_por=user)

        resp = _auth_client(user).get(f"/solicitudes/{sol.id}/trazabilidad")
        assert resp.status_code == 200

        area_events = [e for e in resp.json()["data"]["timeline"] if e["tipo"] == "AREA_INCORPORADA"]
        assert len(area_events) == 2
        # Deterministic: alphabetically by descripcion
        assert area_events[0]["descripcion"] < area_events[1]["descripcion"]


class TestTrazabilidadQueryCount:
    """Query cardinality: no N+1 growth."""

    def test_no_n_plus_1_queries(self, db):
        """Query count stays bounded as graph complexity grows."""
        from django.db import connection

        user = _make_user("admin6", "99999999", "Admin6", "User")
        user2 = _make_user("u2", "10101010", "U2", "Two")
        user3 = _make_user("u3", "11111112", "U3", "Three")
        tipo_doc = TipoDocumento.objects.get(nombre="SOLICITUD")
        exp = _make_exp(6, user, tipo_doc)
        sol = _make_solicitud(exp, user)
        base = datetime.now(timezone.utc)

        # 3 areas × 2 periods × 2 participants × 1 response
        areas = [Area.objects.create(nombre=n, activo=True) for n in ["A", "B", "C"]]
        for i, area in enumerate(areas):
            asig = SolicitudAsignacion.objects.create(
                solicitud=sol, area=area, fecha_incorporacion=base - timedelta(hours=10 - i), incorporado_por=user,
            )
            p1 = _add_periodo(asig, 1, TipoParticipacion.PRINCIPAL, user, base - timedelta(hours=10 - i), EstadoPeriodo.CERRADO, base - timedelta(hours=4 - i))
            _add_participante(p1, user, "Resp", user, base - timedelta(hours=10 - i))
            _add_participante(p1, user2, "Rev", user, base - timedelta(hours=9 - i))
            _add_respuesta(p1, TipoRespuesta.INFORME, EstadoRespuesta.EMITIDA, user, base - timedelta(hours=5 - i))
            p2 = _add_periodo(asig, 2, TipoParticipacion.ADJUNTA, user, base - timedelta(hours=3 - i), EstadoPeriodo.EN_GESTION)
            _add_participante(p2, user3, "Resp", user, base - timedelta(hours=3 - i))
            _add_respuesta(p2, TipoRespuesta.OBSERVACION, EstadoRespuesta.EMITIDA, user, base - timedelta(hours=1 - i))

        connection.queries_log.clear()
        resp = _auth_client(user).get(f"/solicitudes/{sol.id}/trazabilidad")

        assert resp.status_code == 200
        qcount = len(connection.queries)
        assert qcount <= 15, f"Query count {qcount} exceeds budget 15"

        data = resp.json()["data"]
        assert len(data["areas"]) == 3
        assert sum(len(a["etapas"]) for a in data["areas"]) == 6
