"""
ExpedienteCreacionFlujo — flujo async para creación atómica de Expediente con archivos.

transaction.atomic() vive AQUÍ — en el flujo que coordina la creación
compuesta de expediente + archivos.
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
from asgiref.sync import sync_to_async

from django.db import transaction
from injector import inject

from modules.tramites.domain.models import Expediente
from modules.tramites.presentation.schemas.expediente_in import (
    ExpedienteCreateIn,
    ExpedienteArchivoCreateIn,
)
from modules.tramites.domain.services.core.expediente_core_service import (
    ExpedienteCoreService,
)
from modules.tramites.domain.services.core.expediente_archivo_core_service import (
    ExpedienteArchivoCoreService,
)


class ExpedienteCreacionFlujo:
    """
    Flujo asíncrono para creación de Expediente con sus archivos adjuntos.

    Coordina la creación atómica de:
    1. Expediente (cabecera del trámite)
    2. ExpedienteArchivo (documento principal y anexos)

    El @transaction.atomic() garantiza que si falla la creación de cualquier
    archivo, se revierte todo.
    """

    @inject
    def __init__(
        self,
        expediente_core: ExpedienteCoreService,
        archivo_core: ExpedienteArchivoCoreService,
    ):
        self.expediente_core = expediente_core
        self.archivo_core = archivo_core

    async def _proceso_crear_expediente(
        self,
        data: ExpedienteCreateIn,
        usuario_id: int,
    ) -> Expediente:
        """
        Flujo para crear un expediente con sus archivos adjuntos de forma atómica.

        1. Crea el expediente sin archivos.
        2. Por cada archivo en el payload, lo asocia al expediente.
        3. Si cualquier operación falla, se revierte todo.

        Args:
            data: Schema ExpedienteCreateIn con datos del expediente y archivos.
            usuario_id: ID del usuario que realiza el registro.

        Returns:
            Instancia de Expediente creada con sus archivos asociados.
        """
        expediente = await sync_to_async(self._creacion_atomica)(
            data=data,
            usuario_id=usuario_id,
        )
        return expediente

    @transaction.atomic()
    def _creacion_atomica(
        self,
        data: ExpedienteCreateIn,
        usuario_id: int,
    ) -> Expediente:
        """
        Creación atómica de expediente + archivos.

        @transaction.atomic() garantiza que si falla la creación de archivos,
        se revierte el expediente creado.
        """
        # 0. Validar exactamente un archivo PRINCIPAL
        principal_count = len(data.archivos.principal)
        if principal_count != 1:
            from core.exceptions import BusinessError
            raise BusinessError(
                f"Debe haber exactamente 1 archivo PRINCIPAL. Encontrados: {principal_count}",
                code="ARCHIVO_PRINCIPAL_INVALIDO",
            )

        # 1. Crear el expediente
        expediente = self.expediente_core._crear_expediente(
            data=data,
            creado_por_id=usuario_id,
        )

        # 2. Crear los archivos asociados
        archivos_agrupados = data.archivos

        # Archivos principales
        for archivo_data in archivos_agrupados.principal:
            self._crear_archivo_desde_data(
                expediente=expediente,
                archivo_data=archivo_data,
                usuario_id=usuario_id,
            )

        # Archivos anexos
        for archivo_data in archivos_agrupados.anexo:
            self._crear_archivo_desde_data(
                expediente=expediente,
                archivo_data=archivo_data,
                usuario_id=usuario_id,
            )

        return expediente

    def _crear_archivo_desde_data(
        self,
        expediente: Expediente,
        archivo_data: ExpedienteArchivoCreateIn,
        usuario_id: int,
    ) -> None:
        """
        Helper síncrono para crear un archivo desde su schema de datos.

        Args:
            expediente: Instancia de Expediente.
            archivo_data: Schema ExpedienteArchivoCreateIn con los datos del archivo.
            usuario_id: ID del usuario que crea el archivo.
        """
        self.archivo_core._crear_archivo(
            expediente=expediente,
            tipo_archivo=archivo_data.tipo_archivo,
            archivo=archivo_data.archivo,
            nombre_original=archivo_data.nombre_original,
            descripcion=archivo_data.descripcion,
            creado_por_id=usuario_id,
        )