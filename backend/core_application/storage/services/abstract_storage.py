"""
AbstractStorageService — port interface and implementations for file storage.

Provides a unified interface for storing files either:
- Locally via Django's default FileSystemStorage
- In SAAA remote storage (uploads bytes, returns pointer string)

Design principles:
- Injectable/testable — no global state, no mock.patch
- Accepts Django UploadedFile objects
- Returns a string suitable for FileField.name (local path or SAAA pointer)
- Safe to call with string pointers (returns them unchanged — for backward compat)

The returned value is stored directly in FileField.name:
- Local path (e.g. "tramites/expedientes/doc.pdf") → Django's storage backend
  wrote the file; the path is the reference stored in DB.
- SAAA pointer (e.g. "saaa/semana-ingenieria-2026/abc12345/doc.pdf") → bytes were
  uploaded to SAAA; the pointer is stored as a string reference. Django's
  storage backend is NOT invoked for SAAA pointers (no local file is written).

Usage in ExpedienteArchivoCoreService._crear_archivo():
    archivo_storage_path = storage_service.save(archivo, nombre_original)
    ExpedienteArchivo.objects.create(archivo=archivo_storage_path, ...)

The caller is responsible for wrapping the ORM create in transaction.atomic().
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from core_application.storage.pointer import build_saaa_pointer

if TYPE_CHECKING:
    from modules.tramites.domain.ports.saaa_ports import AbstractSaaaClient
    from modules.tramites.infrastructure.saaa_client import FakeSaaaClient, RealSaaaClient


def _saaa_client_provider() -> "AbstractSaaaClient":
    """
    Factory that returns the appropriate SAAA client (real or fake).
    Mirrors the SAAA_USE_FAKE logic from di.py — kept here to avoid circular imports.

    For FakeSaaaClient, uses get_instance() to properly access the singleton.
    For RealSaaaClient, creates a new instance (no singleton needed).
    """
    env_fake = os.environ.get("SAAA_USE_FAKE", "").lower()
    use_fake = env_fake not in ("false", "0", "no") and (
        env_fake != "" or getattr(settings, "SAAA_USE_FAKE", settings.DEBUG)
    )
    if use_fake:
        from modules.tramites.infrastructure.saaa_client import FakeSaaaClient
        return FakeSaaaClient.get_instance()
    else:
        from modules.tramites.infrastructure.saaa_client import RealSaaaClient
        return RealSaaaClient()


@dataclass(frozen=True)
class StorageResult:
    """
    Result of a storage save operation.

    Attributes:
        storage_path: The value to store in FileField.name. For local files,
            this is the Django storage path. For SAAA, this is the SAAA pointer
            string (saaa/{app_id}/{archivo_id}/{nombre_original}).
        is_saaa: True if the file was stored in SAAA, False if local.
    """
    storage_path: str
    is_saaa: bool


class AbstractStorageService(ABC):
    """
    Port interface for file storage.

    Implementations decide whether to upload to SAAA or store locally,
    and return the appropriate string to store in FileField.name.
    """

    @abstractmethod
    def save(self, uploaded_file, nombre_original: str) -> str:
        """
        Save an uploaded file and return the value for FileField.name.

        Args:
            uploaded_file: Django UploadedFile or similar file-like object.
                May also be a string (SAAA pointer or local path) — in that
                case, returns it unchanged for backward compatibility.
            nombre_original: Original filename (used for SAAA pointer construction
                and as a fallback for local storage naming).

        Returns:
            String suitable for FileField.name — either a local storage path
            or a SAAA pointer string (saaa/{app_id}/{archivo_id}/{nombre_original}).
        """
        ...


class LocalStorageService(AbstractStorageService):
    """
    Local file storage using Django's default FileSystemStorage.

    Saves UploadedFile content to Django's configured storage backend
    (typically filesystem under MEDIA_ROOT) and returns the storage path.
    """

    def save(self, uploaded_file, nombre_original: str) -> str:
        """
        Saves the uploaded file to Django's default local storage.

        Reads the UploadedFile content and passes it to Django's storage
        backend, which writes it to MEDIA_ROOT.

        Args:
            uploaded_file: Django UploadedFile object.
            nombre_original: Original filename, used as the storage name.

        Returns:
            Local storage path (e.g. "tramites/expedientes/documento.pdf").
        """
        if isinstance(uploaded_file, str):
            # Backward compat: already a path/pointer string, return as-is
            return uploaded_file

        # Read content once (consumes the UploadedFile)
        content = uploaded_file.read()

        # Reset file pointer so Django/storage can read it if needed
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

        # Save via Django's default storage (FileSystemStorage by default)
        saved_name = default_storage.save(nombre_original, ContentFile(content))

        return saved_name


class SaaaStorageService(AbstractStorageService):
    """
    SAAA remote storage service.

    Uploads file content to the SAAA microservice and returns the SAAA pointer
    string (saaa/{app_id}/{archivo_id}/{nombre_original}) to store in
    FileField.name.

    The SAAA pointer format is a reference to a remote file — no local file
    is written. Django's FileSystemStorage is bypassed entirely for SAAA files.

    DI: inject AbstractSaaaClient via constructor.
    """

    def __init__(self):
        """
        SAAA client is resolved via module-level provider to avoid circular DI issues
        with @inject on __init__ (injector.CallError resolution failure).
        """
        self._saaa = _saaa_client_provider()

    def _get_app_id(self) -> str:
        """Returns the SAAA app_id from settings."""
        return getattr(settings, "SAAA_APP_ID", "semana-ingenieria-2026")

    def save(self, uploaded_file, nombre_original: str) -> str:
        """
        Uploads file to SAAA and returns the SAAA pointer string.

        Reads the UploadedFile content and POSTs it to SAAA via the injected
        client. The SAAA response includes the archivo_id assigned by SAAA.
        The returned pointer string (saaa/{app_id}/{archivo_id}/{nombre_original})
        is stored in FileField.name as a reference to the remote file.

        For backward compat, if a string is passed (already a pointer or path),
        returns it unchanged.

        Args:
            uploaded_file: Django UploadedFile object.
            nombre_original: Original filename (used for SAAA upload and pointer).

        Returns:
            SAAA pointer string: saaa/{app_id}/{archivo_id}/{nombre_original}
        """
        if isinstance(uploaded_file, str):
            # Backward compat: already a path/pointer string, return as-is
            return uploaded_file

        # Read content once (consumes the UploadedFile)
        content = uploaded_file.read()

        # Reset file pointer (not used by SAAA but good hygiene)
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

        # Upload to SAAA
        result = self._saaa.subir_archivo(
            file_content=content,
            nombre_original=nombre_original,
            aplicacion_id=self._get_app_id(),
            usuario_id=getattr(settings, "SAAA_USUARIO_ID", "1"),
            tipo_archivo_id=getattr(settings, "SAAA_TIPO_ARCHIVO_ID", "1"),
        )

        # Build the SAAA pointer string to store in FileField.name
        pointer = build_saaa_pointer(
            app_id=self._get_app_id(),
            archivo_id=result.id,
            nombre_original=nombre_original,
        )

        return pointer
