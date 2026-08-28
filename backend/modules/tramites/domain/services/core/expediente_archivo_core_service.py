"""
ExpedienteArchivoCoreService — operaciones ORM síncronas para ExpedienteArchivo.

NO usa transaction.atomic() internamente — el flujo (flujo) provee la
transacción atómica cuando necesita crear el archivo junto con el expediente.
"""
from django.core.files.uploadedfile import UploadedFile

from injector import inject

from modules.tramites.domain.models import ExpedienteArchivo, Expediente
from modules.tramites.domain.constants import TipoArchivo


class ExpedienteArchivoCoreService:
    """
    Operaciones síncronas para ExpedienteArchivo.

    Toda operación es sync y no abre transaction.atomic() internamente.
    El flujo que la调用 provee la atomicidad si es necesaria.
    """

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
        return ExpedienteArchivo.objects.create(
            expediente=expediente,
            tipo_archivo=tipo_archivo,
            archivo=archivo,
            nombre_original=nombre_original,
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
