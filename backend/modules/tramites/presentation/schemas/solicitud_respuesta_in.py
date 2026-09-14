"""
Esquemas HTTP request para SolicitudRespuesta — Schema Ninja para API.

Usa el patrón dual payload (FormData + archivos):
    data: JSON string con los campos de la respuesta
    files: lista de archivos con nombre con formato "token___nombre_real.ext"
"""
from typing import Optional

from ninja import Field
from django.core.files.uploadedfile import UploadedFile

from core.types import BaseSchema
from modules.asignaciones.domain.constants import TipoRespuesta


class ArchivoAdjuntoRespuestaCreateIn(BaseSchema):
    """
    Schema para un archivo adjunto en la respuesta de una solicitud.

    El campo `archivo` es un UploadedFile que se hidrata via token
    en el patrón dual payload (parse_form_json).
    """

    nombre_original: str = Field(..., min_length=1, max_length=255, description="Nombre original del archivo")
    mime_type: Optional[str] = Field(None, description="Tipo MIME del archivo")
    tamano_bytes: Optional[int] = Field(None, ge=0, description="Tamaño en bytes del archivo")
    archivo: UploadedFile = Field(..., description="Archivo upload (token en FormData)")


class FinalizarSolicitudIn(BaseSchema):
    """
    Payload para emitir una respuesta formal a una Solicitud (finalizar).

    Se recibe via FormData con el patrón dual payload:
        data: JSON string con este schema
        files: lista de UploadedFile con nombres "token___nombre_real.ext"

    El flujo:
    1. Valida que la Solicitud existe y no está FINALIZADA/ANULADA.
    2. Infiere area/periodo del contexto del usuario autenticado.
    3. Obtiene o crea la conversación vinculada.
    4. Crea Mensaje(tipo=SISTEMA) con los archivos adjuntos.
    5. Crea SolicitudRespuesta vinculada.
    6. Si es_final=True: transiciona Solicitud a FINALIZADA y cierra conversación.
    7. Emite notificación RESPUESTA_FINAL al área y al creador.
    """

    tipo_respuesta: str = Field(
        ...,
        description="Tipo de respuesta: INFORME | OBSERVACION | CONFORMIDAD | DESCARGO | OTRO",
    )
    contenido: Optional[str] = Field(
        None,
        description="Contenido textual de la respuesta (requerido si no hay archivos)",
    )
    es_final: bool = Field(
        False,
        description="Si True, esta respuesta cierra la solicitud (default: False)",
    )
    archivos: list[ArchivoAdjuntoRespuestaCreateIn] = Field(
        default_factory=list,
        description="Archivos adjuntos a la respuesta",
    )
