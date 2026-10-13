"""
Tests para AbstractStorageService implementations (SaaaStorageService and LocalStorageService).

Validates:
- SaaaStorageService.save() with FakeSaaaClient returns correct SAAA pointer format.
- SaaaStorageService.save() with string input returns string unchanged (backward compat).
- LocalStorageService.save() returns a local path.
- ExpedienteArchivoCoreService._crear_archivo() with SaaaStorageService stores
  the SAAA pointer in ExpedienteArchivo.archivo.name (not the UploadedFile itself).
"""
import pytest

from django.core.files.uploadedfile import SimpleUploadedFile

from core_application.storage.services import (
    AbstractStorageService,
    LocalStorageService,
    SaaaStorageService,
)
from core_application.storage.pointer import is_saaa_pointer, parse_saaa_pointer

from modules.tramites.domain.models import ExpedienteArchivo
from modules.tramites.domain.constants import TipoArchivo
from modules.tramites.infrastructure.saaa_client import FakeSaaaClient


class TestSaaaStorageServiceSave:
    """Tests for SaaaStorageService.save()."""

    @pytest.fixture
    def storage_service(self):
        """SaaaStorageService instance using FakeSaaaClient (singleton)."""
        return SaaaStorageService()

    @pytest.fixture
    def sample_file(self):
        """SimpleUploadedFile for testing."""
        content = b"PDF content here %PDF-1.4 test file"
        return SimpleUploadedFile(
            name="documento.pdf",
            content=content,
            content_type="application/pdf",
        )

    def test_save_returns_saaa_pointer_format(self, storage_service, sample_file):
        """
        GIVEN: a valid UploadedFile and FakeSaaaClient
        WHEN:  SaaaStorageService.save() is called
        THEN:  it returns a string in format saaa/{app_id}/{archivo_id}/{nombre_original}
        """
        result = storage_service.save(sample_file, "documento.pdf")

        assert result.startswith("saaa/")
        assert is_saaa_pointer(result)
        pointer = parse_saaa_pointer(result)
        assert pointer is not None
        assert pointer.nombre_original == "documento.pdf"
        assert pointer.archivo_id is not None
        assert len(pointer.archivo_id) > 0

    def test_save_returns_saaa_pointer_with_correct_app_id(
        self, storage_service, sample_file, settings
    ):
        """
        GIVEN: a valid UploadedFile
        WHEN:  SaaaStorageService.save() is called
        THEN:  the SAAA pointer contains the configured SAAA_APP_ID
        """
        result = storage_service.save(sample_file, "acta.pdf")

        pointer = parse_saaa_pointer(result)
        # The app_id should match SAAA_APP_ID from settings or default
        assert pointer.app_id == getattr(settings, "SAAA_APP_ID", "semana-ingenieria-2026")

    def test_save_with_string_input_returns_unchanged(self, storage_service):
        """
        GIVEN: a string input (already a pointer or path)
        WHEN:  SaaaStorageService.save() is called
        THEN:  it returns the string unchanged (backward compat)
        """
        string_input = "saaa/semana-ingenieria-2026/abc12345/doc.pdf"
        result = storage_service.save(string_input, "ignored.pdf")

        assert result == string_input

    def test_save_with_local_path_string_returns_unchanged(self, storage_service):
        """
        GIVEN: a local file path string
        WHEN:  SaaaStorageService.save() is called
        THEN:  it returns the string unchanged (backward compat)
        """
        string_input = "tramites/expedientes/documento.pdf"
        result = storage_service.save(string_input, "ignored.pdf")

        assert result == string_input

    def test_save_content_is_uploaded_to_saaa(self, storage_service, sample_file):
        """
        GIVEN: a valid UploadedFile
        WHEN:  SaaaStorageService.save() is called
        THEN:  the returned SAAA pointer contains a non-empty archivo_id,
               proving the fake SAAA server assigned an ID (i.e., accepted the upload).
        """
        # Reset the FakeSaaaClient singleton to ensure clean state
        FakeSaaaClient.reset_instance()

        result = storage_service.save(sample_file, "test.pdf")

        # The SAAA pointer format is saaa/{app_id}/{archivo_id}/{nombre_original}
        # A non-empty archivo_id proves the fake SAAA server processed the upload
        assert result.startswith("saaa/")
        parts = result.split("/")
        assert len(parts) == 4, f"Expected 4 parts in SAAA pointer, got: {parts}"
        archivo_id = parts[2]
        assert len(archivo_id) > 0, "archivo_id should be non-empty (proves upload was processed)"


class TestLocalStorageServiceSave:
    """Tests for LocalStorageService.save()."""

    @pytest.fixture
    def storage_service(self):
        """LocalStorageService instance."""
        return LocalStorageService()

    @pytest.fixture
    def sample_file(self):
        """SimpleUploadedFile for testing."""
        content = b"Local file content for testing"
        return SimpleUploadedFile(
            name="local_doc.pdf",
            content=content,
            content_type="application/pdf",
        )

    def test_save_returns_string_path(self, storage_service, sample_file):
        """
        GIVEN: a valid UploadedFile
        WHEN:  LocalStorageService.save() is called
        THEN:  it returns a string path (the saved filename in Django storage)
        """
        result = storage_service.save(sample_file, "local_doc.pdf")

        assert isinstance(result, str)
        assert len(result) > 0
        # Django's FileSystemStorage may add a random suffix to avoid collisions,
        # so we check that it starts with the base name we passed
        assert result.startswith("local_doc")

    def test_save_with_string_input_returns_unchanged(self, storage_service):
        """
        GIVEN: a string input
        WHEN:  LocalStorageService.save() is called
        THEN:  it returns the string unchanged (backward compat)
        """
        string_input = "tramites/expedientes/doc.pdf"
        result = storage_service.save(string_input, "ignored.pdf")

        assert result == string_input


class TestExpedienteArchivoCoreServiceSaaaIntegration:
    """Integration tests: ExpedienteArchivoCoreService._crear_archivo() with storage service."""

    @pytest.fixture
    def expediente_and_user(self, db):
        """Create minimal Expediente and User for testing."""
        from django.contrib.auth import get_user_model
        from django.utils.timezone import now
        from modules.tramites.domain.models import Expediente
        from modules.tramites.domain.constants import TipoPersona
        from modules.tramites.domain.models import TipoDocumento

        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username="test_saaa_integration",
            defaults={"email": "test@example.com"},
        )

        # Get an existing TipoDocumento or create one
        tipo_doc, _ = TipoDocumento.objects.get_or_create(
            nombre="SOLICITUD",
            defaults={"descripcion": "Solicitud generic"},
        )

        # numero must be provided explicitly — SQLite doesn't support auto-increment
        # the same way as PostgreSQL; the AutoNumeroModel.save() auto-assigns but
        # we provide an explicit value to avoid conflicts
        expediente = Expediente.objects.create(
            numero=99999,
            tipo_persona=TipoPersona.NATURAL,
            nombres="Test",
            apellidos="Integration",
            dni="12345678",
            numero_folios=1,
            asunto="Test SAAA integration expediente",
            tipo_documento=tipo_doc,
            numero_documento="DOC-TEST-99999",
            fecha_registro=now(),
            creado_por=user,
        )
        return expediente, user

    @pytest.fixture
    def sample_file(self):
        """SimpleUploadedFile for testing."""
        content = b"Expediente file content for SAAA test"
        return SimpleUploadedFile(
            name="expediente_test.pdf",
            content=content,
            content_type="application/pdf",
        )

    @pytest.mark.django_db
    def test_crear_archivo_stores_saaa_pointer_not_uploadedfile(
        self, expediente_and_user, sample_file
    ):
        """
        GIVEN: ExpedienteArchivoCoreService with SaaaStorageService (uses FakeSaaaClient)
        WHEN:  _crear_archivo() is called with a real UploadedFile
        THEN:  the created ExpedienteArchivo.archivo.name is a SAAA pointer string,
               NOT the UploadedFile's name attribute.
        """
        from modules.tramites.domain.services.core.expediente_archivo_core_service import (
            ExpedienteArchivoCoreService,
        )

        expediente, user = expediente_and_user
        service = ExpedienteArchivoCoreService(
            storage_service=SaaaStorageService()
        )

        archivo = service._crear_archivo(
            expediente=expediente,
            tipo_archivo=TipoArchivo.PRINCIPAL,
            archivo=sample_file,
            nombre_original="expediente_test.pdf",
            descripcion="Test SAAA integration",
            creado_por_id=user.id,
        )

        # Key assertion: the stored value is a SAAA pointer string,
        # not the original UploadedFile.name
        assert is_saaa_pointer(archivo.archivo.name), (
            f"Expected SAAA pointer, got: {archivo.archivo.name}"
        )
        assert archivo.archivo.name != sample_file.name

    @pytest.mark.django_db
    def test_crear_archivo_nombre_original_is_preserved(
        self, expediente_and_user, sample_file
    ):
        """
        GIVEN: ExpedienteArchivoCoreService with SaaaStorageService
        WHEN:  _crear_archivo() is called
        THEN:  the nombre_original field is stored correctly (not lost)
        """
        from modules.tramites.domain.services.core.expediente_archivo_core_service import (
            ExpedienteArchivoCoreService,
        )

        expediente, user = expediente_and_user
        service = ExpedienteArchivoCoreService(
            storage_service=SaaaStorageService()
        )

        archivo = service._crear_archivo(
            expediente=expediente,
            tipo_archivo=TipoArchivo.ANEXO,
            archivo=sample_file,
            nombre_original="mi_documento.pdf",
            descripcion=None,
            creado_por_id=user.id,
        )

        # nombre_original is stored in a separate field — should match what was passed
        assert archivo.nombre_original == "mi_documento.pdf"

    @pytest.mark.django_db
    def test_crear_archivo_saaa_pointer_contains_nombre_original(
        self, expediente_and_user, sample_file
    ):
        """
        GIVEN: ExpedienteArchivoCoreService with SaaaStorageService
        WHEN:  _crear_archivo() is called
        THEN:  the stored SAAA pointer includes the original filename
        """
        from modules.tramites.domain.services.core.expediente_archivo_core_service import (
            ExpedienteArchivoCoreService,
        )

        expediente, user = expediente_and_user
        service = ExpedienteArchivoCoreService(
            storage_service=SaaaStorageService()
        )

        archivo = service._crear_archivo(
            expediente=expediente,
            tipo_archivo=TipoArchivo.PRINCIPAL,
            archivo=sample_file,
            nombre_original="test_saaa_ptr.pdf",
            descripcion="Test",
            creado_por_id=user.id,
        )

        pointer = parse_saaa_pointer(archivo.archivo.name)
        assert pointer is not None
        assert is_saaa_pointer(archivo.archivo.name)
        assert pointer.nombre_original == "test_saaa_ptr.pdf"
