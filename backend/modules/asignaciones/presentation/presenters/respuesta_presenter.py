"""
RespuestaPresenter — transforma la entidad SolicitudAsignacionRespuesta a esquema HTTP RespuestaOut.
"""
from core_application.storage.resolvers import resolve_public_url
from modules.asignaciones.domain.models.respuesta import SolicitudAsignacionRespuesta
from modules.asignaciones.presentation.schemas.respuesta_out import RespuestaOut


class RespuestaPresenter:
    """
    Transforma objetos SolicitudAsignacionRespuesta del dominio a esquemas de respuesta HTTP.
    Desacopla el formateo de respuesta de los controladores.
    """

    @staticmethod
    def present(respuesta: SolicitudAsignacionRespuesta) -> RespuestaOut:
        """
        Transforma una entidad SolicitudAsignacionRespuesta a RespuestaOut.

        NOTE: respuesta.archivo puede ser un puntero SAAA
        (saaa/{app_id}/{archivo_id}/{nombre}) en lugar de un archivo local.
        resolve_public_url() distingue ambos casos y retorna la URL correcta:
        - SAAA pointer -> /api/archivo/public/{archivo_id}
        - Local file  -> archivo.url (local media URL)

        Args:
            respuesta: Entidad SolicitudAsignacionRespuesta del modelo de dominio

        Returns:
            Esquema RespuestaOut listo para respuesta HTTP
        """
        archivo_url = resolve_public_url(
            respuesta.archivo.name if respuesta.archivo else None,
            respuesta.archivo if respuesta.archivo else None,
        )
        return RespuestaOut(
            id=respuesta.id,
            periodo_id=respuesta.periodo_id,
            tipo_respuesta=respuesta.tipo_respuesta,
            contenido=respuesta.contenido,
            archivo=archivo_url,
            estado=respuesta.estado,
            version=respuesta.version,
            observacion=respuesta.observacion,
            fecha_emision=respuesta.fecha_emision,
            emitido_por_id=respuesta.emitido_por_id,
            created_at=respuesta.created_at,
            updated_at=respuesta.updated_at,
        )
