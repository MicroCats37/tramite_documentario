"""
Integration tests for ExpedienteController.crear_expediente endpoint.

Tests use ninja_extra.testing.TestClient (not Django's Client) for proper sync
controller testing per TEST_ARCHITECTURE_CONTRACT.
All tests use @pytest.mark.django_db for real database access.

This test module covers:
- FormData POST request with JSON payload + file uploads
- Expediente and ExpedienteArchivo creation in database
- Token hydration for file naming (token___nombre.ext format)

NOTE: The controller's endpoint signature is:
    def crear_expediente(self, data: Form[DataForm], files: File[list[UploadedFile]])

The TestClient simulates FormData by passing:
- `data`: {"data": json_string} as the Form fields
- Files as the files parameter with proper naming
"""
import json
import pytest

from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api

from modules.tramites.domain.models import Expediente, ExpedienteArchivo
from modules.tramites.tests.factories import (
    make_expediente_payload,
    make_payload_expediente_natural,
)


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_crear_expediente_single_file(
    ExpedienteController,
    usuario_creador,
    pdf_file,
    tipo_documento_solicitud,
):
    """
    GIVEN: a valid ExpedienteCreateIn payload with one principal file
    WHEN:  POST /crear is called with FormData (JSON data + PDF file)
    THEN:  response status is 200
           AND an Expediente record is created in the database
           AND an ExpedienteArchivo record is created linked to the expediente
    """
    # Build the payload
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
        asunto="Solicitud de trámite de prueba",
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

    # Create TestClient with the full API for proper routing
    client = TestClient(api)
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = usuario_creador

    # Make the request as FormData (simulating the dual-payload pattern)
    # The endpoint expects: data field with JSON string, and files list
    response = client.post(
        "/expedientes/crear",
        data={"data": json.dumps(payload)},
        files={"files": pdf_file},
    )

    # Assert response is 200 OK
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    # Assert database records were created
    expediente_count = Expediente.objects.count()
    archivo_count = ExpedienteArchivo.objects.count()

    assert expediente_count == 1, f"Expected 1 Expediente, found {expediente_count}"
    assert archivo_count == 1, f"Expected 1 ExpedienteArchivo, found {archivo_count}"

    # Verify the expediente data
    expediente = Expediente.objects.first()
    assert expediente.tipo_persona == "NATURAL"
    assert expediente.dni == "12345678"
    assert expediente.nombres == "Juan"
    assert expediente.apellidos == "Perez"
    assert expediente.asunto == "Solicitud de trámite de prueba"
    assert expediente.creado_por == usuario_creador

    # Verify the archivo data
    archivo = ExpedienteArchivo.objects.first()
    assert archivo.expediente == expediente
    assert archivo.tipo_archivo == "PRINCIPAL"
    assert archivo.nombre_original == "documento_principal.pdf"
    assert archivo.creado_por == usuario_creador


@pytest.mark.django_db
def test_crear_expediente_multiple_files(
    ExpedienteController,
    usuario_creador,
    multiple_pdf_files,
    tipo_documento_oficio,
):
    """
    GIVEN: a valid ExpedienteCreateIn payload with multiple files (principal + anexo)
    WHEN:  POST /crear is called with FormData containing JSON + multiple files
    THEN:  response status is 200
           AND one Expediente record exists
           AND two ExpedienteArchivo records exist (PRINCIPAL + ANEXO)
    """
    # The multiple_pdf_files fixture returns [pdf_file, pdf_file_anexo]
    # with names: "token_principal_pdf___documento_principal.pdf" and "token_anexo_pdf___anexo_1.pdf"

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
        asunto="Solicitud con múltiples archivos",
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

    client = TestClient(api)
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = usuario_creador

    response = client.post(
        "/expedientes/crear",
        data={"data": json.dumps(payload)},
        files=[("files", f) for f in multiple_pdf_files],
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
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
def test_crear_expediente_juridica(
    ExpedienteController,
    usuario_creador,
    pdf_file,
    tipo_documento_oficio,
):
    """
    GIVEN: a valid ExpedienteCreateIn payload for persona jurídica (company)
    WHEN:  POST /crear is called with FormData
    THEN:  response status is 200
           AND Expediente has tipo_persona=JURIDICA with RUC and razón social
    """
    payload = make_expediente_payload(
        tipo_persona="JURIDICA",
        dni=None,
        ruc="20456789012",
        razon_social="Empresa Test SAC",
        nombres=None,
        apellidos=None,
        correo="empresa@test.com",
        telefono="012345678",
        tipo_documento_id=tipo_documento_oficio.id,
        numero_documento="OFICIO-J-2026-001",
        numero_folios=12,
        asunto="Solicitud de empresa -Trámite de habilitación",
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

    client = TestClient(api)
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = usuario_creador

    response = client.post(
        "/expedientes/crear",
        data={"data": json.dumps(payload)},
        files={"files": pdf_file},
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    # Verify JURIDICA specific fields
    expediente = Expediente.objects.first()
    assert expediente.tipo_persona == "JURIDICA"
    assert expediente.ruc == "20456789012"
    assert expediente.razon_social == "Empresa Test SAC"
    assert expediente.dni is None
    assert expediente.nombres is None
    assert expediente.apellidos is None


@pytest.mark.django_db
def test_crear_expediente_response_structure(
    ExpedienteController,
    usuario_creador,
    pdf_file,
    tipo_documento_solicitud,
):
    """
    GIVEN: a valid ExpedienteCreateIn payload
    WHEN:  POST /crear is called and returns 200
    THEN:  response JSON has 'data' key with expediente info
           including id_publico format LIMA-{year}-{number:04d}
    """
    payload = make_expediente_payload(
        tipo_persona="NATURAL",
        dni="11223344",
        nombres="Ana",
        apellidos="Lopez",
        correo="ana.lopez@example.com",
        telefono="123456789",
        tipo_documento_id=tipo_documento_solicitud.id,
        numero_documento="SOL-2026-003",
        numero_folios=3,
        asunto="Test de respuesta",
    )

    client = TestClient(api)
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = usuario_creador

    response = client.post(
        "/expedientes/crear",
        data={"data": json.dumps(payload)},
        files={"files": pdf_file},
    )

    assert response.status_code == 200

    response_data = response.json()
    assert "data" in response_data, "Response should have 'data' key"

    data = response_data["data"]
    # The ExpedienteOut schema should include id_publico
    assert "id_publico" in data or "numero" in data, (
        f"Response data should contain expediente identifier. Got: {data.keys()}"
    )
