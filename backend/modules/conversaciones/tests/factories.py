"""
Fixtures — Pure Python payload builders for conversaciones module.

These are NOT fixtures (no db dependency), just pure functions that return dicts.
Import directly in tests:

    from modules.conversaciones.tests.factories import make_conversacion_payload

Payload structures match the domain models.
"""

import uuid
from datetime import datetime, timedelta, timezone


def make_conversacion_payload(
    *,
    titulo: str = "Conversación de prueba",
    creada_por_id: uuid.UUID = None,
    fecha_inicio: datetime = None,
    fecha_cierre: datetime = None,
    cerrado_por_id: uuid.UUID = None,
) -> dict:
    """
    Build a dict payload for creating a Conversacion.

    Args:
        titulo: Título opcional de la conversación.
        creada_por_id: UUID del usuario creador.
        fecha_inicio: Fecha de inicio (default: now).
        fecha_cierre: Fecha de cierre (optional).
        cerrado_por_id: UUID del usuario que cierra (optional).

    Returns:
        dict matching Conversacion fields.
    """
    if fecha_inicio is None:
        fecha_inicio = datetime.now(timezone.utc)

    payload = {
        "titulo": titulo,
        "creada_por_id": str(creada_por_id) if creada_por_id else None,
        "fecha_inicio": fecha_inicio.isoformat(),
    }
    if fecha_cierre is not None:
        payload["fecha_cierre"] = fecha_cierre.isoformat()
    if cerrado_por_id is not None:
        payload["cerrado_por_id"] = str(cerrado_por_id)

    return payload


def make_mensaje_payload(
    *,
    conversacion_id: uuid.UUID,
    autor_usuario_id: uuid.UUID,
    contenido: str = "Contenido del mensaje de prueba",
    tipo: str = "MENSAJE",
    fecha_envio: datetime = None,
    mensaje_padre_id: uuid.UUID = None,
    editado_at: datetime = None,
    eliminado_at: datetime = None,
    eliminado_por_id: uuid.UUID = None,
) -> dict:
    """
    Build a dict payload for creating a Mensaje.

    Args:
        conversacion_id: UUID de la conversación padre.
        autor_usuario_id: UUID del usuario autor.
        contenido: Texto del mensaje.
        tipo: Tipo de mensaje (MENSAJE, RESPUESTA, SISTEMA).
        fecha_envio: Fecha de envío (default: now).
        mensaje_padre_id: UUID del mensaje padre en thread (optional).
        editado_at: Fecha de edición (optional).
        eliminado_at: Fecha de eliminación (optional).
        eliminado_por_id: UUID del usuario que elimina (optional).

    Returns:
        dict matching Mensaje fields.
    """
    if fecha_envio is None:
        fecha_envio = datetime.now(timezone.utc)

    payload = {
        "conversacion_id": str(conversacion_id),
        "autor_usuario_id": str(autor_usuario_id),
        "contenido": contenido,
        "tipo": tipo,
        "fecha_envio": fecha_envio.isoformat(),
    }
    if mensaje_padre_id is not None:
        payload["mensaje_padre_id"] = str(mensaje_padre_id)
    if editado_at is not None:
        payload["editado_at"] = editado_at.isoformat()
    if eliminado_at is not None:
        payload["eliminado_at"] = eliminado_at.isoformat()
    if eliminado_por_id is not None:
        payload["eliminado_por_id"] = str(eliminado_por_id)

    return payload


def make_mensaje_archivo_adjunto_payload(
    *,
    mensaje_id: uuid.UUID,
    nombre_original: str = "documento.pdf",
    mime_type: str = "application/pdf",
    tamano_bytes: int = 1024,
    subido_por_id: uuid.UUID,
    fecha_archivo: datetime = None,
) -> dict:
    """
    Build a dict payload for creating a MensajeArchivoAdjunto.

    Note: archivo is a FileField — the dict here represents metadata only.
    The actual file upload is handled separately in tests.

    Args:
        mensaje_id: UUID del mensaje padre.
        nombre_original: Nombre original del archivo.
        mime_type: Tipo MIME del archivo.
        tamano_bytes: Tamaño en bytes.
        subido_por_id: UUID del usuario que subió.
        fecha_archivo: Fecha de subida (default: now).

    Returns:
        dict matching MensajeArchivoAdjunto metadata fields.
    """
    if fecha_archivo is None:
        fecha_archivo = datetime.now(timezone.utc)

    return {
        "mensaje_id": str(mensaje_id),
        "nombre_original": nombre_original,
        "mime_type": mime_type,
        "tamano_bytes": tamano_bytes,
        "subido_por_id": str(subido_por_id),
        "fecha_archivo": fecha_archivo.isoformat(),
    }


def make_mensaje_mencion_payload(
    *,
    mensaje_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> dict:
    """
    Build a dict payload for creating a MensajeMencion.

    Args:
        mensaje_id: UUID del mensaje que contiene la mención.
        usuario_id: UUID del usuario mencionado.

    Returns:
        dict matching MensajeMencion fields.
    """
    return {
        "mensaje_id": str(mensaje_id),
        "usuario_id": str(usuario_id),
    }


def make_solicitud_conversacion_payload(
    *,
    solicitud_id: uuid.UUID,
    conversacion_id: uuid.UUID,
) -> dict:
    """
    Build a dict payload for creating a SolicitudConversacion bridge.

    Args:
        solicitud_id: UUID de la solicitud.
        conversacion_id: UUID de la conversación.

    Returns:
        dict matching SolicitudConversacion fields.
    """
    return {
        "solicitud_id": str(solicitud_id),
        "conversacion_id": str(conversacion_id),
    }
