"""
ExpedienteArchivoCoreService — operaciones ORM síncronas para ExpedienteArchivo.

NO usa transaction.atomic() internamente — el flujo (flujo) provee la
transacción atómica cuando necesita crear el archivo junto con el expediente.
"""
from django.core.files.uploadedfile import UploadedFile

from injector import inject

from modules.tramites.domain.models import ExpedienteArchivo, Expediente, Archivo
from modules.tramites.domain.constants import TipoArchivo
from core_application.storage.services import AbstractStorageService
from core_application.storage.archivo_factory import create_archivo_from_storage_result


class ExpedienteArchivoCoreService:
    """
    Operaciones síncronas para ExpedienteArchivo.

    Toda operación es sync y no abre transaction.atomic() internamente.
    El flujo que la调用 provee la atomicidad si es necesaria.
    """

    @inject
    def __init__(self, storage_service: AbstractStorageService):
        """
        Args:
            storage_service: AbstractStorageService implementation injected via DI.
                Handles file storage (local or SAAA) and returns the appropriate
                string to store in FileField.name.
        """
        self._storage = storage_service

    def _crear_archivo(
        self,
        expediente: Expediente,
        tipo_archivo: TipoArchivo,
        archivo: UploadedFile,
        nombre_original: str,
        descripcion: str | None,
        creado_por_id: int,
    ) -> ExpedienteArchivo:
        """
        Crea un ExpedienteArchivo asociado a un Expediente.

        Two-step process:
        1. Upload file to storage and create central Archivo record.
        2. Create ExpedienteArchivo with FK to the new Archivo.

        Sync — para uso dentro de transaction.atomic.

        Args:
            expediente: Instancia de Expediente al que se asociará el archivo.
            tipo_archivo: Tipo de archivo (PRINCIPAL o ANEXO).
            archivo: Instancia de UploadedFile con el archivo.
            nombre_original: Nombre original del archivo.
            descripcion: Descripción opcional del archivo.
            creado_por_id: ID del usuario que crea el registro.

        Returns:
            Instancia de ExpedienteArchivo creada.
        """
        # Step 1: Delegate to storage service to get storage reference string
        archivo_storage_path = self._storage.save(archivo, nombre_original)

        # Step 2: Create central Archivo record from storage result
        archivo_obj = create_archivo_from_storage_result(
            storage_path=archivo_storage_path,
            nombre_original=nombre_original,
            subido_por_id=creado_por_id,
        )
        archivo_obj.save()

        # Step 3: Create ExpedienteArchivo with FK to Archivo
        return ExpedienteArchivo.objects.create(
            expediente=expediente,
            tipo_archivo=tipo_archivo,
            archivo=archivo_obj,
            descripcion=descripcion,
            creado_por_id=creado_por_id,
        )

    def _obtener_archivos_por_expediente(
        self, expediente: Expediente
    ) -> list[ExpedienteArchivo]:
        """
        Obtiene todos los archivos asociados a un expediente.

        Sync — para uso dentro de transaction.atomic.
        """
        return list(expediente.archivos.all())
