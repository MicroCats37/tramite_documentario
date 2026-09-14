"""
SolicitudRespuestaCoreService — operaciones ORM síncronas para SolicitudRespuesta.

NO usa transaction.atomic() internamente — el flujo (flujo) provee la
transacción atómica cuando necesita crear respuesta + mensaje + archivos juntos.
"""
from uuid import UUID

from modules.tramites.domain.models import SolicitudRespuesta
from modules.tramites.domain.schemas.solicitud_respuesta_schemas import (
    SolicitudRespuestaCreateData,
)


class SolicitudRespuestaCoreService:
    """
    Operaciones síncronas para SolicitudRespuesta.

    Toda operación es sync y no abre transaction.atomic() internamente.
    El flujo que la llama provee la atomicidad si es necesaria.
    """

    def _crear_respuesta(
        self,
        data: SolicitudRespuestaCreateData,
        conversacion_id: UUID,
        mensaje_id: UUID,
        area_id: UUID,
        area_nombre: str,
        periodo_id: UUID | None,
        emitido_por_id: UUID,
        emitido_por_nombre: str,
        mensaje_archivos: list[dict],
    ) -> "SolicitudRespuestaResult":
        """
        Crea una SolicitudRespuesta y retorna un result object.

        Sync — para uso dentro de transaction.atomic.

        Args:
            data: Datos de la respuesta.
            conversacion_id: UUID de la conversación asociada.
            mensaje_id: UUID del mensaje SISTEMA en la conversación.
            area_id: UUID del área que emite la respuesta.
            area_nombre: Nombre del área (para el result).
            periodo_id: UUID del período asociado (puede ser None).
            emitido_por_id: ID del usuario que emite la respuesta.
            emitido_por_nombre: Nombre del usuario que emite (para el result).
            mensaje_archivos: Lista de dicts con metadata de archivos adjuntos.

        Returns:
            SolicitudRespuestaResult con la respuesta creada y su contexto.
        """
        respuesta = SolicitudRespuesta.objects.create(
            solicitud_id=data.solicitud_id,
            conversacion_id=conversacion_id,
            mensaje_id=mensaje_id,
            area_id=area_id,
            periodo_id=periodo_id,
            tipo_respuesta=data.tipo_respuesta,
            contenido=data.contenido,
            es_final=data.es_final,
            emitido_por_id=emitido_por_id,
        )

        from modules.tramites.domain.results.solicitud_respuesta_result import (
            SolicitudRespuestaResult,
        )

        return SolicitudRespuestaResult(
            respuesta_id=respuesta.id,
            solicitud_id=respuesta.solicitud_id,
            conversacion_id=respuesta.conversacion_id,
            mensaje_id=respuesta.mensaje_id,
            area_id=area_id,
            area_nombre=area_nombre,
            periodo_id=periodo_id,
            tipo_respuesta=respuesta.tipo_respuesta,
            contenido=respuesta.contenido,
            es_final=respuesta.es_final,
            fecha_emision=respuesta.fecha_emision,
            emitido_por_id=emitido_por_id,
            emitido_por_nombre=emitido_por_nombre,
            mensaje_archivos=mensaje_archivos,
        )
