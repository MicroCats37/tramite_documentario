"""
E2E tests for Solicitud Fase 2 API.

Tests cover:
- 2.1: crear solicitud sin áreas → REGISTRADA
- 2.2: fecha_inicio_gestion en primera distribución
- 2.3: un archivo principal en crear-completo
- 2.4: antecedentes en crear-completo
- 2.5: numeración concurrente (lógica de select_for_update)
- 2.6: idempotency-key en crear-completo
- 2.7: presenter incluye asignaciones y archivos

Uses ninja_extra.testing.TestClient (sync) per TEST_ARCHITECTURE_CONTRACT.
Controllers are now sync (contrato P3).

URLs: POST /solicitudes/crear
      POST /solicitudes/crear-completo
"""
import json
from unittest.mock import patch
from datetime import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api

from modules.tramites.domain.models import (
    Expediente,
    ExpedienteArchivo,
    ExpedienteAntecedente,
    Solicitud,
    SolicitudEstadoHistorial,
    TipoDocumento,
)
from modules.asignaciones.domain.models import (
    SolicitudAsignacion,
    SolicitudAsignacionPeriodo,
)
from modules.usuarios.domain.models import Area


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def usuario_creador_sol(db):
    """Create a test user for Solicitud creation."""
    User = get_user_model()
    return User.objects.create_user(
        username="operador_sol",
        email="operador_sol@cip.gob.pe",
        password="testpass123",
        dni="55443322",
        nombres="Maria",
        apellidos="Gonzalez",
    )


@pytest.fixture
def area_test(db):
    """Create a test area."""
    return Area.objects.create(
        nombre="Área de Prueba",
        descripcion="Área para tests",
        activo=True,
    )


@pytest.fixture
def pdf_file_principal():
    """Create a principal PDF file."""
    return SimpleUploadedFile(
        name="token_principal_pdf___documento_principal.pdf",
        content=b"%PDF-1.4 test content",
        content_type="application/pdf",
    )


@pytest.fixture
def pdf_file_anexo():
    """Create an annex PDF file."""
    return SimpleUploadedFile(
        name="token_anexo_pdf___anexo_1.pdf",
        content=b"%PDF-1.4 annex content",
        content_type="application/pdf",
    )


# ── Helpers ─────────────────────────────────────────────────────────────────

class AuthTestClient(TestClient):
    """TestClient that sends the same Bearer JWT contract used by production."""

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._auth_user = user
        self._access_token = str(AccessToken.for_user(user))

    def request(self, method, path, data=None, json=None, **request_params):
        headers = dict(getattr(self, "headers", {}))
        headers.update(request_params.pop("headers", {}))
        headers.setdefault("Authorization", f"Bearer {self._access_token}")
        request_params["headers"] = headers
        return super().request(method, path, data, json, **request_params)


def _make_auth_client(user):
    """Create a ninja_extra TestClient with auth for the given user."""
    return AuthTestClient(user=user, router_or_app=api)


def _build_solicitud_hibrida_payload(
    *,
    expediente_data: dict,
    areas_distribucion: list = None,
    antecedentes: list = None,
) -> dict:
    """
    Build a SolicitudHibridaCreateIn payload dict for FormData.

    If expediente_data contains tipo_documento_id as a TipoDocumento instance
    (instead of a UUID string), it is converted to str(id).
    """
    if areas_distribucion is None:
        areas_distribucion = []
    if antecedentes is None:
        antecedentes = []

    exp = expediente_data.copy()
    # Normalize tipo_documento_id: if it's a TipoDocumento instance, use its id.
    td_id = exp.get("tipo_documento_id")
    if td_id is not None:
        from modules.tramites.domain.models import TipoDocumento
        if isinstance(td_id, TipoDocumento):
            exp["tipo_documento_id"] = str(td_id.id)
    elif exp.get("tipo_documento") is not None:
        # Legacy: convert string nombre to UUID via DB lookup.
        from modules.tramites.domain.models import TipoDocumento
        td_nombre = exp.pop("tipo_documento")
        exp["tipo_documento_id"] = str(TipoDocumento.objects.get(nombre=td_nombre).id)

    return {
        "prioridad": "MEDIA",
        "observacion": None,
        "areas_distribucion": areas_distribucion,
        "antecedentes": antecedentes,
        "expediente": exp,
    }


def _crear_expediente_directo(usuario, numero, **kwargs):
    """Create an Expediente row directly for /crear tests."""
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
        numero_documento=f"DOC-2026-{numero:03d}",
        numero_folios=5,
        asunto="Trámite de prueba",
        fecha_registro=datetime.now(),
        creado_por=usuario,
    )
    defaults.update(kwargs)
    return Expediente.objects.create(**defaults)


# ── Task 2.1: crear solicitud sin áreas → REGISTRADA ──────────────────────────

@pytest.mark.django_db
def test_crear_solicitud_sin_areas(usuario_creador_sol):
    """
    GIVEN: an existing Expediente (created separately) and a user
    WHEN:  POST /solicitudes/crear is called with empty areas_distribucion
    THEN:  response status is 200
            AND Solicitud.estado == REGISTRADA
            AND no SolicitudAsignacion records exist
            AND no SolicitudAsignacionPeriodo records exist
    """
    expediente = _crear_expediente_directo(
        usuario_creador_sol,
        numero=1,
        asunto="Trámite sin áreas",
    )

    payload = {
        "expediente_id": str(expediente.id),
        "prioridad": "MEDIA",
        "observacion": None,
        "areas_distribucion": [],
    }

    client = _make_auth_client(usuario_creador_sol)
    response = client.post(
        "/solicitudes/crear",
        json=payload,
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["estado"] == "REGISTRADA", (
        f"Expected REGISTRADA, got {data['estado']}"
    )

    assert SolicitudAsignacion.objects.count() == 0
    assert SolicitudAsignacionPeriodo.objects.count() == 0


# ── Task 2.2: fecha_inicio_gestion en primera distribución ───────────────────

@pytest.mark.django_db
def test_fecha_inicio_gestion_en_primera_distribucion(usuario_creador_sol, area_test):
    """
    GIVEN: an existing Expediente
    WHEN:  POST /solicitudes/crear is called with one area
    THEN:  Solicitud.fecha_inicio_gestion is set
            AND a SolicitudEstadoHistorial record shows REGISTRADA → EN_GESTION
            AND Solicitud.estado == EN_GESTION
    """
    expediente = _crear_expediente_directo(
        usuario_creador_sol,
        numero=2,
        dni="87654321",
        nombres="Pedro",
        apellidos="Lopez",
        correo="pedro@test.com",
        telefono="988776655",
        tipo_documento="OFICIO",
        asunto="Trámite con área",
    )

    payload = {
        "expediente_id": str(expediente.id),
        "prioridad": "ALTA",
        "observacion": None,
        "areas_distribucion": [
            {
                "area_id": str(area_test.id),
                "tipo_participacion": "PRINCIPAL",
                "observacion": None,
            }
        ],
    }

    client = _make_auth_client(usuario_creador_sol)
    response = client.post(
        "/solicitudes/crear",
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
        "fecha_inicio_gestion should be set when areas are provided"
    )

    solicitud = Solicitud.objects.get(id=data["id"])
    historial = SolicitudEstadoHistorial.objects.filter(
        solicitud=solicitud
    ).order_by("fecha_cambio")
    estados = list(historial.values_list("estado_nuevo", flat=True))
    assert estados == ["REGISTRADA", "EN_GESTION"], (
        f"Expected [REGISTRADA, EN_GESTION], got {estados}"
    )


# ── Task 2.3: un archivo principal en crear-completo ──────────────────────────

@pytest.mark.django_db
def test_un_solo_archivo_principal(usuario_creador_sol, pdf_file_anexo):
    """
    GIVEN: a valid SolicitudHibridaCreateIn payload with 0 PRINCIPAL files
    WHEN:  POST /solicitudes/crear-completo is called
    THEN:  response status is 400
            AND error code is ARCHIVO_PRINCIPAL_INVALIDO
    """
    payload = _build_solicitud_hibrida_payload(
        expediente_data={
            "tipo_persona": "NATURAL",
            "dni": "11223344",
            "nombres": "Ana",
            "apellidos": "Martinez",
            "correo": "ana@test.com",
            "telefono": "911922933",
            "tipo_documento": "SOLICITUD",
            "numero_documento": "DOC-2026-003",
            "numero_folios": 2,
            "asunto": "Trámite sin principal",
            "archivos": {
                "principal": [],
                "anexo": [
                    {
                        "tipo_archivo": "ANEXO",
                        "nombre_original": "anexo_1.pdf",
                        "descripcion": "Anexo",
                        "archivo": "token_anexo_pdf",
                    }
                ],
            },
        },
    )

    with patch(
        "django.core.files.storage.FileSystemStorage.save",
        return_value="expedientes/archivos/dummy.pdf",
    ):
        client = _make_auth_client(usuario_creador_sol)
        response = client.post(
            "/solicitudes/crear-completo",
            data={"data": json.dumps(payload), "files": pdf_file_anexo},
        )

    assert response.status_code == 400, (
        f"Expected 400, got {response.status_code}: {response.content}"
    )
    error = response.json()["error"]
    assert error["code"] == "ARCHIVO_PRINCIPAL_INVALIDO", (
        f"Expected ARCHIVO_PRINCIPAL_INVALIDO, got {error['code']}"
    )


@pytest.mark.django_db
def test_mas_de_un_archivo_principal(usuario_creador_sol, pdf_file_principal):
    """
    GIVEN: a valid SolicitudHibridaCreateIn payload with 2 PRINCIPAL files
    WHEN:  POST /solicitudes/crear-completo is called
    THEN:  response status is 400
            AND error code is ARCHIVO_PRINCIPAL_INVALIDO
    """
    pdf_file_principal_2 = SimpleUploadedFile(
        name="token_principal2_pdf___documento2.pdf",
        content=b"%PDF-1.4 test content 2",
        content_type="application/pdf",
    )

    payload = _build_solicitud_hibrida_payload(
        expediente_data={
            "tipo_persona": "NATURAL",
            "dni": "22334455",
            "nombres": "Carlos",
            "apellidos": "Diaz",
            "correo": "carlos@test.com",
            "telefono": "922933944",
            "tipo_documento": "SOLICITUD",
            "numero_documento": "DOC-2026-004",
            "numero_folios": 4,
            "asunto": "Trámite con múltiples principales",
            "archivos": {
                "principal": [
                    {
                        "tipo_archivo": "PRINCIPAL",
                        "nombre_original": "doc1.pdf",
                        "descripcion": "Principal 1",
                        "archivo": "token_principal_pdf",
                    },
                    {
                        "tipo_archivo": "PRINCIPAL",
                        "nombre_original": "doc2.pdf",
                        "descripcion": "Principal 2",
                        "archivo": "token_principal2_pdf",
                    },
                ],
                "anexo": [],
            },
        },
    )

    with patch(
        "django.core.files.storage.FileSystemStorage.save",
        return_value="expedientes/archivos/dummy.pdf",
    ):
        client = _make_auth_client(usuario_creador_sol)
        response = client.post(
            "/solicitudes/crear-completo",
            data={
                "data": json.dumps(payload),
                "files": [pdf_file_principal, pdf_file_principal_2],
            },
        )

    assert response.status_code == 400, (
        f"Expected 400, got {response.status_code}: {response.content}"
    )
    error = response.json()["error"]
    assert error["code"] == "ARCHIVO_PRINCIPAL_INVALIDO"


# ── Task 2.4: antecedentes en crear-completo ───────────────────────────────

@pytest.mark.django_db
def test_creacion_con_antecedentes(usuario_creador_sol, pdf_file_principal):
    """
    GIVEN: an existing Expediente to be used as antecedent
    WHEN:  POST /solicitudes/crear-completo is called with antecedentes
    THEN:  ExpedienteAntecedente records are created
            AND they are linked to the new Expediente
    """
    antecedente_expediente = _crear_expediente_directo(
        usuario_creador_sol,
        numero=999,
        dni="33445566",
        nombres="Luis",
        apellidos="Perez",
        correo="luis@test.com",
        telefono="933944055",
        numero_documento="DOC-ANT-001",
        asunto="Expediente antecedente",
    )

    payload = _build_solicitud_hibrida_payload(
        expediente_data={
            "tipo_persona": "NATURAL",
            "dni": "44556677",
            "nombres": "Elena",
            "apellidos": "Ruiz",
            "correo": "elena@test.com",
            "telefono": "944055166",
            "tipo_documento": "SOLICITUD",
            "numero_documento": "DOC-2026-005",
            "numero_folios": 3,
            "asunto": "Trámite con antecedente",
            "archivos": {
                "principal": [
                    {
                        "tipo_archivo": "PRINCIPAL",
                        "nombre_original": "documento.pdf",
                        "descripcion": "Documento principal",
                        "archivo": "token_principal_pdf",
                    }
                ],
                "anexo": [],
            },
        },
        antecedentes=[
            {
                "antecedente_id": str(antecedente_expediente.id),
                "categoria": "subsanacion",
                "observaciones": "Documentación incompleta anterior",
            }
        ],
    )

    with patch(
        "django.core.files.storage.FileSystemStorage.save",
        return_value="expedientes/archivos/dummy.pdf",
    ):
        client = _make_auth_client(usuario_creador_sol)
        response = client.post(
            "/solicitudes/crear-completo",
            data={"data": json.dumps(payload), "files": pdf_file_principal},
        )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    new_expediente = Expediente.objects.order_by("-created_at").first()
    antecedente_record = ExpedienteAntecedente.objects.filter(
        expediente=new_expediente,
        antecedente=antecedente_expediente,
    ).first()

    assert antecedente_record is not None, (
        "ExpedienteAntecedente record should exist"
    )
    assert antecedente_record.categoria == "subsanacion"
    assert (
        antecedente_record.observaciones == "Documentación incompleta anterior"
    )


# ── Task 2.5: numeración concurrente (lógica de select_for_update) ────────────

@pytest.mark.django_db
def test_numeracion_concurrente_sin_duplicados(usuario_creador_sol, pdf_file_principal):
    """
    GIVEN: two crear-completo requests for different expedientes in the same year
    WHEN:  both are processed sequentially
    THEN:  each gets a unique numero
            AND no UniqueViolation occurs
    """
    payload_base = _build_solicitud_hibrida_payload(
        expediente_data={
            "tipo_persona": "NATURAL",
            "dni": "55667788",
            "nombres": "Roberto",
            "apellidos": "Sanchez",
            "correo": "roberto@test.com",
            "telefono": "955066277",
            "tipo_documento": "SOLICITUD",
            "numero_folios": 1,
            "asunto": "Trámite numerado 1",
            "archivos": {
                "principal": [
                    {
                        "tipo_archivo": "PRINCIPAL",
                        "nombre_original": "doc1.pdf",
                        "descripcion": "Principal",
                        "archivo": "token_principal_pdf",
                    }
                ],
                "anexo": [],
            },
        },
    )

    with patch(
        "django.core.files.storage.FileSystemStorage.save",
        return_value="expedientes/archivos/dummy.pdf",
    ):
        client = _make_auth_client(usuario_creador_sol)

        payload1 = dict(payload_base)
        payload1["expediente"] = dict(payload_base["expediente"])
        payload1["expediente"]["numero_documento"] = "DOC-SEQ-001"
        response1 = client.post(
            "/solicitudes/crear-completo",
            data={"data": json.dumps(payload1), "files": pdf_file_principal},
        )

        assert response1.status_code == 200, (
            f"First request failed: {response1.status_code}: {response1.content}"
        )

        payload2 = dict(payload_base)
        payload2["expediente"] = dict(payload_base["expediente"])
        payload2["expediente"]["numero_documento"] = "DOC-SEQ-002"
        response2 = client.post(
            "/solicitudes/crear-completo",
            data={"data": json.dumps(payload2), "files": pdf_file_principal},
        )

        assert response2.status_code == 200, (
            f"Second request failed: {response2.status_code}: {response2.content}"
        )

    numeros = list(
        Expediente.objects.order_by("numero")
        .values_list("numero", flat=True)
        .exclude(numero=999)
    )
    assert len(numeros) == len(set(numeros)), (
        f"Duplicate numeros found: {numeros}"
    )
    assert numeros[-1] == numeros[0] + 1


# ── Task 2.6: idempotency-key en crear-completo ───────────────────────────────

@pytest.mark.django_db
def test_creacion_idempotente(usuario_creador_sol, pdf_file_principal):
    """
    GIVEN: a valid crear-completo payload
    WHEN:  POST /solicitudes/crear-completo is called twice
           with the same Idempotency-Key header
    THEN:  first request returns 200 and creates records
            AND second request returns 200 with cached result
            AND no duplicate Expediente or Solicitud records are created
    """
    idempotency_key = "idem-12345678-test"

    payload = _build_solicitud_hibrida_payload(
        expediente_data={
            "tipo_persona": "NATURAL",
            "dni": "66778899",
            "nombres": "Ida",
            "apellidos": "Lopez",
            "correo": "ida@test.com",
            "telefono": "966077388",
            "tipo_documento": "SOLICITUD",
            "numero_documento": "DOC-IDEM-001",
            "numero_folios": 1,
            "asunto": "Trámite idempotente",
            "archivos": {
                "principal": [
                    {
                        "tipo_archivo": "PRINCIPAL",
                        "nombre_original": "doc_idem.pdf",
                        "descripcion": "Principal idempotente",
                        "archivo": "token_principal_pdf",
                    }
                ],
                "anexo": [],
            },
        },
    )

    with patch(
        "django.core.files.storage.FileSystemStorage.save",
        return_value="expedientes/archivos/dummy.pdf",
    ):
        client = _make_auth_client(usuario_creador_sol)
        client.headers["Idempotency-Key"] = idempotency_key

        response1 = client.post(
            "/solicitudes/crear-completo",
            data={"data": json.dumps(payload), "files": pdf_file_principal},
        )

        assert response1.status_code == 200, (
            f"First request failed: {response1.status_code}: {response1.content}"
        )

        exp_count_before = Expediente.objects.count()
        sol_count_before = Solicitud.objects.count()

        response2 = client.post(
            "/solicitudes/crear-completo",
            data={"data": json.dumps(payload), "files": pdf_file_principal},
        )

        assert response2.status_code == 200, (
            f"Second request with idempotency key should return 200, "
            f"got {response2.status_code}: {response2.content}"
        )

        assert Expediente.objects.count() == exp_count_before, (
            "No new Expediente should be created on idempotent retry"
        )
        assert Solicitud.objects.count() == sol_count_before, (
            "No new Solicitud should be created on idempotent retry"
        )


# ── Task 2.7: presenter incluye asignaciones y archivos ──────────────────────

@pytest.mark.django_db
def test_presenter_incluye_asignaciones(usuario_creador_sol, area_test, pdf_file_principal):
    """
    GIVEN: a crear-completo request with areas_distribucion
    WHEN:  POST /solicitudes/crear-completo returns 200
    THEN:  response includes expediente with archivos
            AND areas_activas with summary counts
    """
    payload = _build_solicitud_hibrida_payload(
        expediente_data={
            "tipo_persona": "NATURAL",
            "dni": "77889900",
            "nombres": "Paula",
            "apellidos": "Diaz",
            "correo": "paula@test.com",
            "telefono": "977088499",
            "tipo_documento": "SOLICITUD",
            "numero_documento": "DOC-PRES-001",
            "numero_folios": 2,
            "asunto": "Trámite con asignaciones",
            "archivos": {
                "principal": [
                    {
                        "tipo_archivo": "PRINCIPAL",
                        "nombre_original": "doc_pres.pdf",
                        "descripcion": "Documento principal",
                        "archivo": "token_principal_pdf",
                    }
                ],
                "anexo": [
                    {
                        "tipo_archivo": "ANEXO",
                        "nombre_original": "anexo_pres.pdf",
                        "descripcion": "Anexo de prueba",
                        "archivo": "token_anexo_pdf",
                    }
                ],
            },
        },
        areas_distribucion=[
            {
                "area_id": str(area_test.id),
                "tipo_participacion": "PRINCIPAL",
                "observacion": None,
            }
        ],
    )

    pdf_anexo = SimpleUploadedFile(
        name="token_anexo_pdf___anexo_pres.pdf",
        content=b"%PDF-1.4 annex pres",
        content_type="application/pdf",
    )

    with patch(
        "django.core.files.storage.FileSystemStorage.save",
        return_value="expedientes/archivos/dummy.pdf",
    ):
        client = _make_auth_client(usuario_creador_sol)
        response = client.post(
            "/solicitudes/crear-completo",
            data={
                "data": json.dumps(payload),
                "files": [pdf_file_principal, pdf_anexo],
            },
        )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]

    # Response should include nested expediente with archivos
    assert "expediente" in data
    assert "archivos" in data["expediente"], (
        "Response expediente should include archivos"
    )
    assert len(data["expediente"]["archivos"]) == 2, (
        f"Expected 2 archivos (1 principal + 1 anexo), "
        f"got {len(data['expediente']['archivos'])}"
    )

    tipos = {a["tipo_archivo"] for a in data["expediente"]["archivos"]}
    assert "PRINCIPAL" in tipos
    assert "ANEXO" in tipos

    # Response should include areas_activas with counts
    assert "areas_activas" in data
    assert len(data["areas_activas"]) == 1
    assert data["areas_activas"][0]["area_id"] == str(area_test.id)
    assert data["areas_activas"][0]["area_nombre"] == area_test.nombre


# ── Conversation creation tests ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_crear_solicitud_crea_conversacion_vinculada(usuario_creador_sol, area_test):
    """
    GIVEN:  an existing Expediente
    WHEN:   POST /solicitudes/crear is called (solicitud-only flow)
    THEN:   a SolicitudConversacion bridge is created
            AND a Conversacion record exists
            AND the bridge links the solicitud to the conversation
    """
    from modules.conversaciones.domain.models import SolicitudConversacion, Conversacion

    expediente = _crear_expediente_directo(
        usuario_creador_sol,
        numero=100,
        asunto="Trámite con conversación",
    )

    payload = {
        "expediente_id": str(expediente.id),
        "prioridad": "MEDIA",
        "observacion": None,
        "areas_distribucion": [
            {
                "area_id": str(area_test.id),
                "tipo_participacion": "PRINCIPAL",
                "observacion": None,
            }
        ],
    }

    client = _make_auth_client(usuario_creador_sol)
    response = client.post(
        "/solicitudes/crear",
        json=payload,
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    solicitud_id = data["id"]

    # Verify bridge was created
    bridge = SolicitudConversacion.objects.filter(solicitud_id=solicitud_id).first()
    assert bridge is not None, "SolicitudConversacion bridge should exist"

    # Verify Conversacion was created
    conversacion = bridge.conversacion
    assert conversacion is not None, "Conversacion should exist"
    assert conversacion.titulo == f"Conversación - {expediente.id_publico}"
    assert conversacion.fecha_cierre is None, "New conversation should be open"
    assert conversacion.creada_por_id == usuario_creador_sol.id


@pytest.mark.django_db
def test_crear_solicitud_hibrida_crea_conversacion_vinculada(usuario_creador_sol, area_test, pdf_file_principal):
    """
    GIVEN:  a valid SolicitudHibridaCreateIn payload
    WHEN:   POST /solicitudes/crear-completo is called (hybrid flow)
    THEN:   a SolicitudConversacion bridge is created
            AND a Conversacion record exists
    """
    from modules.conversaciones.domain.models import SolicitudConversacion, Conversacion

    payload = _build_solicitud_hibrida_payload(
        expediente_data={
            "tipo_persona": "NATURAL",
            "dni": "11223344",
            "nombres": "Rosa",
            "apellidos": "Morales",
            "correo": "rosa@test.com",
            "telefono": "988776611",
            "tipo_documento": "SOLICITUD",
            "numero_documento": "DOC-CONV-001",
            "numero_folios": 3,
            "asunto": "Trámite híbrido con conversación",
            "archivos": {
                "principal": [
                    {
                        "tipo_archivo": "PRINCIPAL",
                        "nombre_original": "documento.pdf",
                        "descripcion": "Documento principal",
                        "archivo": "token_principal_pdf",
                    }
                ],
                "anexo": [],
            },
        },
        areas_distribucion=[
            {
                "area_id": str(area_test.id),
                "tipo_participacion": "PRINCIPAL",
                "observacion": None,
            }
        ],
    )

    with patch(
        "django.core.files.storage.FileSystemStorage.save",
        return_value="expedientes/archivos/dummy.pdf",
    ):
        client = _make_auth_client(usuario_creador_sol)
        response = client.post(
            "/solicitudes/crear-completo",
            data={"data": json.dumps(payload), "files": pdf_file_principal},
        )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    solicitud_id = data["id"]

    # Verify bridge was created
    bridge = SolicitudConversacion.objects.filter(solicitud_id=solicitud_id).first()
    assert bridge is not None, "SolicitudConversacion bridge should exist"

    # Verify Conversacion was created
    conversacion = bridge.conversacion
    assert conversacion is not None, "Conversacion should exist"
    assert conversacion.fecha_cierre is None, "New conversation should be open"

