"""
SolicitudRespuestaOrchestrator — fachada asíncrona ligera para controladores de SolicitudRespuesta.

Delegación a SolicitudRespuestaFlujo.
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
from uuid import UUID

from injector import inject

from modules.tramites.domain.services.flujos.solicitud_respuesta_flujo import (
    SolicitudRespuestaFlujo,
)


class SolicitudRespuestaOrchestrator:
    """
    Fachada asíncrona ligera — delega a SolicitudRespuestaFlujo.

    Un método público por endpoint del controlador.
    """

    @inject
    def __init__(self, flujo: SolicitudRespuestaFlujo):
        self.flujo = flujo

    async def emitir_respuesta_final(
        self,
        solicitud_id: UUID,
        usuario_id: int,
        tipo_respuesta: str,
        contenido: str | None,
        es_final: bool,
        archivos_data: list[dict] | None = None,
    ):
        """
        Emite una respuesta formal a una Solicitud.

        Args:
            solicitud_id: UUID de la Solicitud.
            usuario_id: ID del usuario que emite la respuesta.
            tipo_respuesta: INFORME | OBSERVACION | CONFORMIDAD | DESCARGO | OTRO.
            contenido: Texto de la respuesta (puede ser None si hay archivos).
            es_final: Si True, esta respuesta cierra la solicitud.
            archivos_data: Lista de dicts con metadata de archivos adjuntos.

        Returns:
            SolicitudRespuestaResult con la respuesta creada.
        """
        return await self.flujo._proceso_emitir_respuesta(
            solicitud_id=solicitud_id,
            usuario_id=usuario_id,
            tipo_respuesta=tipo_respuesta,
            contenido=contenido,
            es_final=es_final,
            archivos_data=archivos_data,
        )
