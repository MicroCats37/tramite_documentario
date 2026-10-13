"""
AbstractSaaaClient — port interface para el cliente SAAA.

Define el contrato que toda implementación (RealSaaaClient, FakeSaaaClient)
debe cumplir. Permite inyección de dependencias y testing sin mocks.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SaaaArchivoResult:
    """
    Resultado de descargar un archivo desde SAAA.

    Attributes:
        id: ID del archivo en SAAA.
        path_relativo: Path relativo del archivo.
        nombre_original: Nombre original del archivo.
        extension: Extensión del archivo.
        contenido: Contenido binario del archivo (ya decodificado de base64).
    """
    id: str
    path_relativo: str
    nombre_original: str
    extension: str
    contenido: bytes


@dataclass(frozen=True)
class SaaaUploadResult:
    """
    Resultado de subir un archivo a SAAA.

    Attributes:
        id: ID asignado por SAAA.
        path_relativo: Path relativo del archivo en SAAA.
        nombre_original: Nombre original enviado.
        extension: Extensión del archivo.
    """
    id: str
    path_relativo: str
    nombre_original: str
    extension: str


class AbstractSaaaClient(ABC):
    """
    Interface para el cliente SAAA.

    SAAA es un microservicio de almacenamiento de archivos que:
    - Recibe archivos via multipart POST
    - Devuelve respuestas con IDs y paths relativos
    - Responde downloads en base64

    Esta interface aísla la comunicación con SAAA del resto de la aplicación.
    """

    @abstractmethod
    def registrar_archivador(self, app_id: str) -> bool:
        """
        Registra o verifica que existe un archivador para la app.

        Args:
            app_id: Identificador de la aplicación (ej. 'semana-ingenieria-2026')

        Returns:
            True si el archivador existe o se creó exitosamente.
        """
        ...

    @abstractmethod
    def subir_archivo(
        self,
        *,
        file_content: bytes,
        nombre_original: str,
        aplicacion_id: str,
        usuario_id: str,
        tipo_archivo_id: str = "1",
    ) -> SaaaUploadResult:
        """
        Sube un archivo a SAAA via multipart.

        Args:
            file_content: Contenido binario del archivo.
            nombre_original: Nombre original del archivo.
            aplicacion_id: ID de la aplicación en SAAA.
            usuario_id: ID del usuario que sube.
            tipo_archivo_id: ID del tipo de archivo (default: "1").

        Returns:
            SaaaUploadResult con el ID y path asignado por SAAA.
        """
        ...

    @abstractmethod
    def descargar_archivo(self, archivo_id: str) -> SaaaArchivoResult:
        """
        Descarga un archivo de SAAA por su ID.

        Args:
            archivo_id: ID del archivo en SAAA.

        Returns:
            SaaaArchivoResult con el contenido binario decodificado.

        Raises:
            SaaaNotFoundError: Si el archivo no existe en SAAA.
            SaaaConnectionError: Si no se puede conectar a SAAA.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """
        Verifica que SAAA está accesible.

        Returns:
            True si SAAA responde correctamente.
        """
        ...
