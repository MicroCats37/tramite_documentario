"""
Expediente fixtures — auth client, user creation, and file upload helpers.

Provides fixtures for testing ExpedienteController.crear_expediente endpoint.

Re-exports: api_client, auth_client, usuario_creador, pdf_file
"""
import pytest
import uuid
from io import BytesIO
from typing import Optional

from django.core.files.uploadedfile import SimpleUploadedFile

from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken
from django.contrib.auth import get_user_model


@pytest.fixture
def api_client(db):
    """
    Ninja TestClient for testing Ninja endpoints with proper async handling.

    Note: This fixture does NOT include ExpedienteController in the API.
    Use auth_client + ExpedienteController directly for expediente tests.
    """
    # Import here to avoid circular imports
    from config.api import api
    return TestClient(api)


@pytest.fixture
def usuario_creador(db):
    """
    Create a test user for Expediente.creado_por FK.

    This user represents the mesa de partes operator who registers the expediente.
    """
    User = get_user_model()
    return User.objects.create_user(
        username="operador_mesa",
        email="operador@cip.gob.pe",
        password="testpass123",
        dni="87654321",
        nombres="Carlos",
        apellidos="Rodriguez",
    )


@pytest.fixture
def auth_client(api_client, usuario_creador):
    """
    JWT-authenticated test client for ExpedienteController tests.

    Sets the Authorization header with a valid JWT token for the test user.
    """
    token = AccessToken.for_user(usuario_creador)
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    api_client.user = usuario_creador
    return api_client


@pytest.fixture
def pdf_file():
    """
    Create a SimpleUploadedFile simulating a PDF upload.

    The file uses the naming convention 'token___nombre.ext' which the
    parse_form_json function expects for file token hydration.

    Returns:
        SimpleUploadedFile with PDF content and proper name format
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
    Create a SimpleUploadedFile simulating an annex PDF upload.

    Returns:
        SimpleUploadedFile with PDF content for an annex document
    """
    pdf_content = b"%PDF-1.4 test content for annex PDF file"
    return SimpleUploadedFile(
        name="token_anexo_pdf___anexo_1.pdf",
        content=pdf_content,
        content_type="application/pdf",
    )


@pytest.fixture
def multiple_pdf_files(pdf_file, pdf_file_anexo):
    """
    Create multiple SimpleUploadedFile objects for testing multi-file uploads.

    Returns:
        list of SimpleUploadedFile objects
    """
    return [pdf_file, pdf_file_anexo]


@pytest.fixture
def ExpedienteController():
    """
    Import and return the ExpedienteController class for direct instantiation.

    Use this to create a TestClient directly with the controller:
        client = TestClient(ExpedienteController)

    This bypasses the main API router and tests the controller in isolation.
    """
    from modules.tramites.presentation.controllers.expediente_controller import ExpedienteController
    return ExpedienteController


@pytest.fixture
def ExpedienteOrchestrator():
    """
    Import and return the ExpedienteOrchestrator class.

    The orchestrator requires ExpedienteCreacionFlujo to be injected.
    """
    from modules.tramites.domain.services.orchestrators.expediente_orchestrator import ExpedienteOrchestrator
    return ExpedienteOrchestrator


@pytest.fixture
def ExpedienteCreacionFlujo():
    """
    Import and return the ExpedienteCreacionFlujo class.

    The flujo requires ExpedienteCoreService and ExpedienteArchivoCoreService to be injected.
    """
    from modules.tramites.domain.services.flujos.expediente_flujo import ExpedienteCreacionFlujo
    return ExpedienteCreacionFlujo


@pytest.fixture
def tipo_documento_solicitud(db):
    """
    Return the SOLICITUD TipoDocumento catalog entry.

    Use this as tipo_documento_solicitud.id for API payloads.
    """
    from modules.tramites.domain.models import TipoDocumento
    return TipoDocumento.objects.get(nombre="SOLICITUD")


@pytest.fixture
def tipo_documento_oficio(db):
    """
    Return the OFICIO TipoDocumento catalog entry.

    Use this as tipo_documento_oficio.id for API payloads.
    """
    from modules.tramites.domain.models import TipoDocumento
    return TipoDocumento.objects.get(nombre="OFICIO")
