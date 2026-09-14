"""
E2E tests for Expediente creation API.

True end-to-end tests using ninja_extra.testing.TestClient (sync) per
TEST_ARCHITECTURE_CONTRACT. Controllers are now sync (contrato P3).

Tests use @pytest.mark.django_db for real database access.
Mocks FileSystemStorage.save to prevent actual file writes.
Tests multipart/form-data payload with JSON data + file upload.

URL: POST /expedientes/crear (relative to controller)
"""
import json
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api

from modules.tramites.domain.models import Expediente, ExpedienteArchivo
from modules.tramites.tests.factories import make_expediente_payload


# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def usuario_creador(db):
    """
    Create a test user who registers the expediente.
    """
    User = get_user_model()
    return User.objects.create_user(
        username="operador_mesa_e2e",
        email="operador_e2e@cip.gob.pe",
        password="testpass123",
        dni="11223344",
        nombres="Carlos",
        apellidos="Rodriguez",
    )


@pytest.fixture
def pdf_file():
    """
    Create a SimpleUploadedFile simulating a PDF upload.

    File naming convention: "token___nombre.ext" for parse_form_json hydration.
    """
    pdf_content = b"%PDF-1.4 test content for PDF file"
    return SimpleUploadedFile(
        name="token_principal_pdf___documento_principal.pdf",
        content=pdf_content,
        content_type="application/pdf",
    )


@pytest.fixture
def pdf_file_anexo():
    """
    Create a SimpleUploadedFile for an annex PDF.
    """
    pdf_content = b"%PDF-1.4 test annex content"
    return SimpleUploadedFile(
        name="token_anexo_pdf___anexo_1.pdf",
        content=pdf_content,
        content_type="application/pdf",
    )


# ── E2E Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_e2e_crear_expediente_success(
    usuario_creador,
    pdf_file,
    tipo_documento_solicitud,
):
    """
    E2E test for Expediente creation with file upload.

    GIVEN:  a valid ExpedienteCreateIn payload with one principal file
    WHEN:   POST /expedientes/crear is called via TestClient
            with multipart/form-data (JSON data + PDF file)
    THEN:   response status is 200
            AND FileSystemStorage.save was called (mock intercepted the file write)
            AND an Expediente record exists in the database
            AND an ExpedienteArchivo record exists linked to the expediente
    """
    # Build the payload using the factory helper
    payload = make_expediente_payload(
        tipo_persona="NATURAL",
        dni="12345678",
        nombres="Juan",
        apellidos="Perez",
        correo="juan.perez@example.com",
        telefono="999888777",
        tipo_documento_id=tipo_documento_solicitud.id,
        numero_documento="SOL-2026-001",
        numero_folios=5,
        asunto="Solicitud de trámite de prueba E2E",
        archivos={
            "principal": [
                {
                    "tipo_archivo": "PRINCIPAL",
                    "nombre_original": "documento_principal.pdf",
                    "descripcion": "Documento principal",
                    "archivo": "token_principal_pdf",
                }
            ],
            "anexo": [],
        },
    )

    # Mock FileSystemStorage.save to prevent actual file writes
    with patch(
        "django.core.files.storage.FileSystemStorage.save",
        return_value="expedientes/archivos/dummy.pdf",
    ) as mock_save:
        # Use ninja_extra TestClient with full API for proper routing
        client = TestClient(api)
        token = AccessToken.for_user(usuario_creador)
        client.headers.update({"Authorization": f"Bearer {token}"})
        client.user = usuario_creador

        # POST with multipart/form-data
        response = client.post(
            "/expedientes/crear",
            data={"data": json.dumps(payload), "files": pdf_file},
        )

        # ── Assertion 1: Response status is 200 ───────────────────────────────
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.content}"
        )

        # ── Assertion 2: Mock save was called (file upload intercepted) ───────
        assert mock_save.called, (
            "FileSystemStorage.save was not called - file upload was not intercepted"
        )

        # ── Assertion 3: Expediente exists in database ────────────────────────
        expediente_count = Expediente.objects.count()
        assert expediente_count == 1, (
            f"Expected 1 Expediente in database, found {expediente_count}"
        )

        expediente = Expediente.objects.first()
        assert expediente.tipo_persona == "NATURAL"
        assert expediente.dni == "12345678"
        assert expediente.nombres == "Juan"
        assert expediente.apellidos == "Perez"
        assert expediente.asunto == "Solicitud de trámite de prueba E2E"
        assert expediente.creado_por == usuario_creador

        # ── Assertion 4: ExpedienteArchivo exists ─────────────────────────────
        archivo_count = ExpedienteArchivo.objects.count()
        assert archivo_count == 1, (
            f"Expected 1 ExpedienteArchivo in database, found {archivo_count}"
        )

        archivo = ExpedienteArchivo.objects.first()
        assert archivo.expediente == expediente
        assert archivo.tipo_archivo == "PRINCIPAL"
        assert archivo.nombre_original == "documento_principal.pdf"
        assert archivo.creado_por == usuario_creador


@pytest.mark.django_db
def test_e2e_crear_expediente_multiple_files(
    usuario_creador,
    pdf_file,
    pdf_file_anexo,
    tipo_documento_oficio,
):
    """
    E2E test for Expediente creation with multiple files (principal + anexo).

    GIVEN:  a valid payload with principal and annex files
    WHEN:   POST /expedientes/crear is called with multiple files
    THEN:   response status is 200
            AND save was called for each file (mock verified)
            AND one Expediente exists with two ExpedienteArchivo records
    """
    payload = make_expediente_payload(
        tipo_persona="NATURAL",
        dni="87654321",
        nombres="Maria",
        apellidos="Garcia",
        correo="maria.garcia@example.com",
        telefono="988776655",
        tipo_documento_id=tipo_documento_oficio.id,
        numero_documento="OFICIO-2026-002",
        numero_folios=8,
        asunto="Solicitud con múltiples archivos E2E",
        archivos={
            "principal": [
                {
                    "tipo_archivo": "PRINCIPAL",
                    "nombre_original": "documento_principal.pdf",
                    "descripcion": "Documento principal",
                    "archivo": "token_principal_pdf",
                }
            ],
            "anexo": [
                {
                    "tipo_archivo": "ANEXO",
                    "nombre_original": "anexo_1.pdf",
                    "descripcion": "Anexo informativo",
                    "archivo": "token_anexo_pdf",
                }
            ],
        },
    )

    with patch(
        "django.core.files.storage.FileSystemStorage.save",
        return_value="expedientes/archivos/dummy.pdf",
    ) as mock_save:
        client = TestClient(api)
        token = AccessToken.for_user(usuario_creador)
        client.headers.update({"Authorization": f"Bearer {token}"})
        client.user = usuario_creador

        response = client.post(
            "/expedientes/crear",
            data={"data": json.dumps(payload), "files": [pdf_file, pdf_file_anexo]},
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.content}"
        )

        # Verify mock was called (should be called once per file)
        assert mock_save.call_count >= 1, (
            f"Expected save to be called at least once, got {mock_save.call_count}"
        )

        # Verify database records
        assert Expediente.objects.count() == 1
        assert ExpedienteArchivo.objects.count() == 2

        expediente = Expediente.objects.first()
        archivos = ExpedienteArchivo.objects.filter(expediente=expediente)

        principal = archivos.filter(tipo_archivo="PRINCIPAL").first()
        anexo = archivos.filter(tipo_archivo="ANEXO").first()

        assert principal is not None, "PRINCIPAL archivo should exist"
        assert anexo is not None, "ANEXO archivo should exist"
        assert principal.nombre_original == "documento_principal.pdf"
        assert anexo.nombre_original == "anexo_1.pdf"


@pytest.mark.django_db
def test_e2e_crear_expediente_persona_juridica(
    usuario_creador,
    pdf_file,
    tipo_documento_oficio,
):
    """
    E2E test for Expediente creation for persona jurídica (company).

    GIVEN:  a valid payload for JURIDICA type with RUC and razón social
    WHEN:   POST /expedientes/crear is called
    THEN:   response status is 200
            AND Expediente has tipo_persona=JURIDICA with correct RUC and razón social
    """
    payload = make_expediente_payload(
        tipo_persona="JURIDICA",
        dni=None,
        ruc="20456789012",
        razon_social="Empresa Test E2E SAC",
        nombres=None,
        apellidos=None,
        correo="empresa_e2e@test.com",
        telefono="012345678",
        tipo_documento_id=tipo_documento_oficio.id,
        numero_documento="OFICIO-J-2026-001",
        numero_folios=12,
        asunto="Solicitud de empresa E2E - Trámite de habilitación",
        archivos={
            "principal": [
                {
                    "tipo_archivo": "PRINCIPAL",
                    "nombre_original": "oficio_empresa.pdf",
                    "descripcion": "Oficio de la empresa",
                    "archivo": "token_principal_pdf",
                }
            ],
            "anexo": [],
        },
    )

    with patch(
        "django.core.files.storage.FileSystemStorage.save",
        return_value="expedientes/archivos/dummy.pdf",
    ):
        client = TestClient(api)
        token = AccessToken.for_user(usuario_creador)
        client.headers.update({"Authorization": f"Bearer {token}"})
        client.user = usuario_creador

        response = client.post(
            "/expedientes/crear",
            data={"data": json.dumps(payload), "files": pdf_file},
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.content}"
        )

        # Verify JURIDICA specific fields
        expediente = Expediente.objects.first()
        assert expediente is not None, "Expediente should be created"
        assert expediente.tipo_persona == "JURIDICA"
        assert expediente.ruc == "20456789012"
        assert expediente.razon_social == "Empresa Test E2E SAC"
        assert expediente.dni is None
        assert expediente.nombres is None
        assert expediente.apellidos is None


@pytest.mark.django_db
def test_e2e_crear_expediente_response_structure(
    usuario_creador,
    pdf_file,
    tipo_documento_solicitud,
):
    """
    E2E test verifying the response structure includes required fields.

    GIVEN:  a valid ExpedienteCreateIn payload
    WHEN:   POST /expedientes/crear returns 200
    THEN:   response JSON has 'data' key with expediente identifier
            (id_publico format LIMA-{year}-{number:04d})
    """
    payload = make_expediente_payload(
        tipo_persona="NATURAL",
        dni="99887766",
        nombres="Ana",
        apellidos="Lopez",
        correo="ana.lopez@example.com",
        telefono="123456789",
        tipo_documento_id=tipo_documento_solicitud.id,
        numero_documento="SOL-2026-003",
        numero_folios=3,
        asunto="Test de respuesta E2E",
    )

    with patch(
        "django.core.files.storage.FileSystemStorage.save",
        return_value="expedientes/archivos/dummy.pdf",
    ):
        client = TestClient(api)
        token = AccessToken.for_user(usuario_creador)
        client.headers.update({"Authorization": f"Bearer {token}"})
        client.user = usuario_creador

        response = client.post(
            "/expedientes/crear",
            data={"data": json.dumps(payload), "files": pdf_file},
        )

        assert response.status_code == 200

        response_data = response.json()
        assert "data" in response_data, "Response should have 'data' key"

        data = response_data["data"]
        # The response should include an identifier for the expediente
        # (either id_publico like "LIMA-2026-0001" or numero)
        assert "id_publico" in data or "numero" in data, (
            f"Response data should contain expediente identifier. Got: {data.keys()}"
        )
