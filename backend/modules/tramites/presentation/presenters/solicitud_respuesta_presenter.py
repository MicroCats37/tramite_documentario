"""
SolicitudRespuestaPresenter — transforma result objects en HTTP schemas.

NO consulta DB — solo transforma el resultado pasado desde el orchestrator.
"""

from modules.tramites.domain.results.solicitud_respuesta_result import (
    SolicitudRespuestaResult,
)
from modules.tramites.domain.constants import EstadoSolicitud
from modules.tramites.presentation.schemas.solicitud_respuesta_out import (
    ArchivoAdjuntoOut,
    SolicitudRespuestaFinalizarOut,
    SolicitudRespuestaOut,
)


class SolicitudRespuestaPresenter:
    """Presenter para SolicitudRespuesta."""

    @staticmethod
    def present_finalizar(
        resultado: SolicitudRespuestaResult,
        solicitud_estado: str,
        fecha_cierre=None,
        conversacion_id=None,
    ) -> SolicitudRespuestaFinalizarOut:
        """
        Transforma el resultado del flujo en el schema de respuesta HTTP.

        Args:
            resultado: SolicitudRespuestaResult del flujo.
            solicitud_estado: Estado actual de la solicitud (después de la operación).
            fecha_cierre: Fecha de cierre (solo si es_final=True).
            conversacion_id: UUID de la conversación.

        Returns:
            SolicitudRespuestaFinalizarOut con todos los campos.
        """
        archivos_out = [
            ArchivoAdjuntoOut(
                id=archivo["id"],
                nombre_original=archivo["nombre_original"],
                mime_type=archivo.get("mime_type"),
                tamano_bytes=archivo.get("tamano_bytes"),
            )
            for archivo in resultado.mensaje_archivos
        ]

        respuesta_out = SolicitudRespuestaOut(
            id=resultado.respuesta_id,
            solicitud_id=resultado.solicitud_id,
            area_id=resultado.area_id,
            area_nombre=resultado.area_nombre,
            periodo_id=resultado.periodo_id,
            tipo_respuesta=resultado.tipo_respuesta,
            contenido=resultado.contenido,
            es_final=resultado.es_final,
            fecha_emision=resultado.fecha_emision,
            emitido_por_id=resultado.emitido_por_id,
            emitido_por_nombre=resultado.emitido_por_nombre,
            archivos=archivos_out,
            created_at=resultado.fecha_emision,  # close enough; uses fecha_emision
        )

        return SolicitudRespuestaFinalizarOut(
            solicitud_respuesta=respuesta_out,
            solicitud_estado=solicitud_estado,
            fecha_cierre=fecha_cierre,
            conversacion_id=conversacion_id or resultado.conversacion_id,
        )
