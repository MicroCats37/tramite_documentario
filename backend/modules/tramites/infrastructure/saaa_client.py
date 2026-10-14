"""
SAAA Client — infraestructura para comunicación con el microservicio SAAA.

Provee dos implementaciones:
- RealSaaaClient: conecta con el servicio SAAA real via HTTP
- FakeSaaaClient: implementación en memoria para tests sin dependencia externa

El cliente SAAA funciona así:
1. POST /archivador/save → registra la aplicación
2. POST /archivo/save (multipart) → sube archivos
3. GET /archivo/find-by-id/{app_id}/{id} → devuelve {bytes: "<base64>"} → proxy Django decodifica

Configuración (environment variables / settings):
    SAAA_URL:              Base URL de SAAA (default: http://172.16.93.83:9007/api/v1)
    SAAA_APP_ID:           ID de aplicación registrado (default: semana-ingenieria-2026)
    SAAA_USUARIO_ID:       ID de usuario por defecto (default: 1)
    SAAA_TIPO_ARCHIVO_ID:  Tipo archivo por defecto (default: 1)
    SAAA_TIMEOUT:          Timeout en segundos (default: 30)
"""
import base64
import uuid
from typing import Optional

import httpx
from django.conf import settings

from modules.tramites.domain.ports.saaa_ports import (
    AbstractSaaaClient,
    SaaaArchivoResult,
    SaaaUploadResult,
)
from modules.tramites.domain.exceptions import (
    SaaaConnectionError,
    SaaaNotFoundError,
    SaaaUploadError,
)


class RealSaaaClient(AbstractSaaaClient):
    """
    Cliente real que conecta con el servicio SAAA via HTTP.

    Lee configuración de django.conf.settings:
        SAAA_URL, SAAA_APP_ID, SAAA_USUARIO_ID, SAAA_TIPO_ARCHIVO_ID, SAAA_TIMEOUT
    """

    def __init__(self):
        self.base_url: str = getattr(settings, "SAAA_URL", "http://172.16.93.83:9007/api/v1").rstrip("/")
        self.app_id: str = getattr(settings, "SAAA_APP_ID", "semana-ingenieria-2026")
        self.usuario_id: str = getattr(settings, "SAAA_USUARIO_ID", "1")
        self.tipo_archivo_id: str = getattr(settings, "SAAA_TIPO_ARCHIVO_ID", "1")
        self.timeout: int = getattr(settings, "SAAA_TIMEOUT", 30)

    def _post_json(self, path: str, json_data: dict) -> dict:
        """Helper para POST con JSON y manejo de errores."""
        url = f"{self.base_url}{path}"
        try:
            response = httpx.post(url, json=json_data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as e:
            raise SaaaConnectionError(f"Timeout conectando a SAAA: {e}")
        except httpx.ConnectError as e:
            raise SaaaConnectionError(f"Error de conexión a SAAA: {e}")
        except httpx.RequestError as e:
            raise SaaaConnectionError(f"Error de red conectando a SAAA: {e}")
        except httpx.HTTPStatusError as e:
            raise SaaaConnectionError(f"SAAA devolvió {e.response.status_code}: {e}")

    def _get_json(self, path: str) -> dict:
        """Helper para GET con manejo de errores."""
        url = f"{self.base_url}{path}"
        try:
            response = httpx.get(url, timeout=self.timeout)
            if response.status_code == 404:
                raise SaaaNotFoundError(path.split("/")[-1])
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as e:
            raise SaaaConnectionError(f"Timeout conectando a SAAA: {e}")
        except httpx.ConnectError as e:
            raise SaaaConnectionError(f"Error de conexión a SAAA: {e}")
        except httpx.RequestError as e:
            raise SaaaConnectionError(f"Error de red conectando a SAAA: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise SaaaNotFoundError(path.split("/")[-1])
            raise SaaaConnectionError(f"SAAA devolvió {e.response.status_code}: {e}")

    def health_check(self) -> bool:
        try:
            self._get_json("/archivador/list")
            return True
        except Exception:
            return False

    def registrar_archivador(self, app_id: Optional[str] = None) -> bool:
        target_id = app_id or self.app_id
        payload = {
            "id": target_id,
            "tipoArchivadorId": "1",
            "autorizacion": True,
        }
        self._post_json("/archivador/save", payload)
        return True

    def subir_archivo(
        self,
        *,
        file_content: bytes,
        nombre_original: str,
        aplicacion_id: Optional[str] = None,
        usuario_id: Optional[str] = None,
        tipo_archivo_id: Optional[str] = None,
    ) -> SaaaUploadResult:
        target_app = aplicacion_id or self.app_id
        target_user = usuario_id or self.usuario_id
        target_tipo = tipo_archivo_id or self.tipo_archivo_id

        url = f"{self.base_url}/archivo/save"
        extension = nombre_original.split(".")[-1] if "." in nombre_original else ""

        try:
            files = {
                "files": (nombre_original, file_content, "application/octet-stream"),
                "aplicacionId": (None, target_app),
                "usuarioId": (None, target_user),
                "tipoArchivoId": (None, target_tipo),
            }
            response = httpx.post(url, files=files, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # La respuesta de SAAA es un array de objetos archivo
            if isinstance(data, list) and len(data) > 0:
                item = data[0]
            elif isinstance(data, dict):
                item = data
            else:
                raise SaaaUploadError(f"Respuesta inesperada de SAAA: {data}")

            return SaaaUploadResult(
                id=str(item.get("id", "")),
                path_relativo=str(item.get("pathRelativo", "")),
                nombre_original=str(item.get("nombreOriginal", nombre_original)),
                extension=str(item.get("extension", extension)),
            )
        except httpx.TimeoutException as e:
            raise SaaaConnectionError(f"Timeout subiendo archivo a SAAA: {e}")
        except httpx.ConnectError as e:
            raise SaaaConnectionError(f"Error de conexión a SAAA: {e}")
        except httpx.RequestError as e:
            raise SaaaConnectionError(f"Error de red subiendo archivo a SAAA: {e}")
        except httpx.HTTPStatusError as e:
            raise SaaaUploadError(f"SAAA devolvió {e.response.status_code}: {e.response.text[:200]}")

    def descargar_archivo(self, archivo_id: str) -> SaaaArchivoResult:
        url = f"{self.base_url}/archivo/find-by-id/{self.app_id}/{archivo_id}"
        try:
            response = httpx.get(url, timeout=self.timeout)
            if response.status_code == 404:
                raise SaaaNotFoundError(archivo_id)
            response.raise_for_status()

            data = response.json()

            # SAAA retorna base64 en campo "bytes" (confirmed from Next.js reference)
            if isinstance(data, dict):
                base64_str = data.get("bytes", "")
                path_relativo = data.get("pathRelativo", "")
                nombre_original = data.get("nombreOriginal", "archivo")
                extension = data.get("extension", "")
            else:
                raise SaaaConnectionError(f"SAAA devolvió formato inesperado: {type(data)}")

            contenido = base64.b64decode(base64_str)

            return SaaaArchivoResult(
                id=archivo_id,
                path_relativo=path_relativo,
                nombre_original=nombre_original,
                extension=extension,
                contenido=contenido,
            )
        except httpx.TimeoutException as e:
            raise SaaaConnectionError(f"Timeout descargando archivo de SAAA: {e}")
        except httpx.ConnectError as e:
            raise SaaaConnectionError(f"Error de conexión a SAAA: {e}")
        except httpx.RequestError as e:
            raise SaaaConnectionError(f"Error de red descargando archivo de SAAA: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise SaaaNotFoundError(archivo_id)
            raise SaaaConnectionError(f"SAAA devolvió {e.response.status_code}: {e}")


class FakeSaaaClient(AbstractSaaaClient):
    """
    Cliente SAAA fake para tests.

    Almacena archivos en memoria y retorna respuestas estructuralmente
    equivalentes a las de SAAA real. Útil para tests sin dependencia
    del servicio externo.

    Para acceso global desde tests:
        fake = FakeSaaaClient.get_instance()
        fake.reset()  # limpia estado entre tests
    """

    _instance: "FakeSaaaClient | None" = None

    def __init__(self):
        if FakeSaaaClient._instance is not None:
            # Ya existe una instancia — reuse para mantener singleton
            self._archivos = FakeSaaaClient._instance._archivos
            self._archivador_registrado = FakeSaaaClient._instance._archivador_registrado
        else:
            self._archivos = {}
            self._archivador_registrado = False
            FakeSaaaClient._instance = self

    def reset(self) -> None:
        """Limpia el estado del cliente fake (entre tests)."""
        self._archivos.clear()
        self._archivador_registrado = False

    @classmethod
    def get_instance(cls) -> "FakeSaaaClient":
        """Retorna la instancia singleton actual, o crea una nueva si no existe."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton. Call between tests for isolation."""
        cls._instance = None

    def health_check(self) -> bool:
        return True

    def registrar_archivador(self, app_id: Optional[str] = None) -> bool:
        self._archivador_registrado = True
        return True

    def subir_archivo(
        self,
        *,
        file_content: bytes,
        nombre_original: str,
        aplicacion_id: Optional[str] = None,
        usuario_id: Optional[str] = None,
        tipo_archivo_id: Optional[str] = "1",
    ) -> SaaaUploadResult:
        archivo_id = str(uuid.uuid4())
        extension = nombre_original.split(".")[-1] if "." in nombre_original else ""
        path_relativo = f"test/{archivo_id}/{nombre_original}"

        result = SaaaArchivoResult(
            id=archivo_id,
            path_relativo=path_relativo,
            nombre_original=nombre_original,
            extension=extension,
            contenido=file_content,
        )
        self._archivos[archivo_id] = result

        return SaaaUploadResult(
            id=archivo_id,
            path_relativo=path_relativo,
            nombre_original=nombre_original,
            extension=extension,
        )

    def descargar_archivo(self, archivo_id: str) -> SaaaArchivoResult:
        if archivo_id not in self._archivos:
            raise SaaaNotFoundError(archivo_id)
        return self._archivos[archivo_id]
