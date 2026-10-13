"""
SaaaArchivoProxyController — endpoint público para servir archivos desde SAAA.

El frontend consume este endpoint de forma transparente, como si fuera
un archivo local. Internamente, el controlador:
1. Recibe el saaa_id desde la URL
2. Consulta el cliente SAAA (inyectado) para obtener el archivo en base64
3. Decodifica el base64 y retorna el contenido binario como streaming response

Este endpoint es público (sin auth) porque los archivos de mesa de partes
son documentos administrativos accesibles sin autenticación.

Ruta: GET /api/archivo/public/{saaa_id}
Tags: ["Archivos"]
"""
import base64
from uuid import UUID

from django.http import HttpResponse

from ninja_extra import api_controller, route
from ninja_extra.permissions import AllowAny
from injector import inject

from modules.tramites.domain.ports.saaa_ports import AbstractSaaaClient
from modules.tramites.domain.exceptions import SaaaNotFoundError, SaaaConnectionError


# MIME types por extensión
_EXTENSION_MIME = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "zip": "application/zip",
}


def _mimetype_for_extension(extension: str) -> str:
    """Retorna el MIME type para una extensión de archivo."""
    ext = extension.lower().lstrip(".")
    return _EXTENSION_MIME.get(ext, "application/octet-stream")


@api_controller(
    "/archivo/public",
    tags=["Archivos"],
    permissions=[AllowAny],
    auth=None,
)
class SaaaArchivoProxyController:
    """
    Proxy público para servir archivos almacenados en SAAA.

    Este controlador es público (sin autenticación) para permitir que el frontend
    acceda a los archivos sin manejar tokens de sesión.
    """

    @inject
    def __init__(self, saaa_client: AbstractSaaaClient):
        self.saaa_client = saaa_client

    @route.get("/{saaa_id}", auth=None)
    async def obtener_archivo_publico(self, request, saaa_id: str):
        """
        Descarga un archivo desde SAAA por su ID y retorna el contenido binario.

        El SAAA retorna el archivo codificado en base64. Este endpoint:
        1. Consulta SAAA para obtener el archivo en base64
        2. Decodifica el base64 a binario
        3. Retorna el binario como streaming response

        Args:
            saaa_id: ID del archivo en SAAA

        Returns:
            StreamingHttpResponse con el contenido binario del archivo
        """
        try:
            archivo = await self._descargar_archivo(saaa_id)
            return self._build_response(archivo)
        except SaaaNotFoundError:
            return HttpResponse(
                content=f"Archivo no encontrado: {saaa_id}",
                status=404,
                content_type="text/plain",
            )
        except SaaaConnectionError as e:
            return HttpResponse(
                content=f"Error de conexión con SAAA: {e}",
                status=502,
                content_type="text/plain",
            )

    async def _descargar_archivo(self, saaa_id: str):
        """
        Wrapper async para descargar archivo del cliente SAAA.

        El cliente SAAA es sync, así que usamos sync_to_async.
        """
        from asgiref.sync import sync_to_async

        return await sync_to_async(self.saaa_client.descargar_archivo)(
            archivo_id=saaa_id
        )

    def _build_response(self, archivo):
        """
        Construye la HttpResponse con el contenido binario del archivo.

        Args:
            archivo: SaaaArchivoResult con el contenido decodificado

        Returns:
            StreamingHttpResponse con el archivo
        """
        from django.http import StreamingHttpResponse

        mimetype = _mimetype_for_extension(archivo.extension)
        filename = archivo.nombre_original

        response = StreamingHttpResponse(
            iter([archivo.contenido]),
            content_type=mimetype,
        )
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        response["Content-Length"] = len(archivo.contenido)
        # Cache header para archivos públicos
        response["Cache-Control"] = "public, max-age=3600"
        return response
