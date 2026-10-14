"""
RespuestaPresenter — transforma la entidad SolicitudAsignacionRespuesta a esquema HTTP RespuestaOut.
"""
from core_application.storage.resolvers import resolve_storage_url
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

        Uses resolve_storage_url() with the Archivo FK's storage_backend and
        storage_reference to produce the correct URL for SAAA, local, or external
        storage backends.

        Args:
            respuesta: Entidad SolicitudAsignacionRespuesta del modelo de dominio

        Returns:
            Esquema RespuestaOut listo para respuesta HTTP
        """
        if respuesta.archivo:
            archivo_url = resolve_storage_url(
                storage_backend=respuesta.archivo.storage_backend,
                storage_reference=respuesta.archivo.storage_reference,
            )
        else:
            archivo_url = None
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
