"""
ExpedientePresenter — transforma la entidad Expediente a esquema HTTP ExpedienteItemOut.
"""
from core_application.storage.resolvers import resolve_public_url
from modules.tramites.domain.models.expediente import Expediente
from modules.tramites.domain.models import ExpedienteArchivo
from modules.tramites.presentation.schemas.expediente_out import ExpedienteArchivoOut
from modules.tramites.presentation.schemas.expediente_list_out import ExpedienteItemOut
from modules.tramites.presentation.schemas.tipo_documento_out import TipoDocumentoOut


class ExpedientePresenter:
    """
    Transforma objetos Expediente del dominio a esquemas de respuesta HTTP.
    Desacopla el formateo de respuesta de los controladores.
    """

    @staticmethod
    def present(expediente: Expediente) -> ExpedienteItemOut:
        """
        Transforma una entidad Expediente a ExpedienteItemOut.

        Incluye archivos adjuntos con URL para que el frontend pueda usar
        directamente sin transformación adicional.

        Args:
            expediente: Entidad Expediente del modelo de dominio

        Returns:
            Esquema ExpedienteItemOut listo para respuesta HTTP (misma forma que list items)
        """
        # Load archivos with eager loading
        archivos_qs = ExpedienteArchivo.objects.filter(expediente=expediente)

        archivos_out = [
            ExpedientePresenter._map_archivo(a)
            for a in archivos_qs
        ]

        return ExpedienteItemOut(
            id=expediente.id,
            id_publico=expediente.id_publico,
            numero=expediente.numero,
            tipo_persona=expediente.tipo_persona,
            dni=expediente.dni,
            ruc=expediente.ruc,
            cip=expediente.cip,
            razon_social=expediente.razon_social,
            nombres=expediente.nombres,
            apellidos=expediente.apellidos,
            correo=expediente.correo,
            telefono=expediente.telefono,
            tipo_documento=TipoDocumentoOut(
                id=expediente.tipo_documento.id,
                nombre=expediente.tipo_documento.nombre,
                descripcion=expediente.tipo_documento.descripcion,
            ),
            numero_documento=expediente.numero_documento,
            numero_folios=expediente.numero_folios,
            asunto=expediente.asunto,
            observaciones=expediente.observaciones,
            fecha_registro=expediente.fecha_registro,
            archivos=archivos_out,
        )

    @staticmethod
    def _map_archivo(archivo: ExpedienteArchivo) -> ExpedienteArchivoOut:
        """Transforma un ExpedienteArchivo a ExpedienteArchivoOut.

        Si archivo.archivo.name es un puntero SAAA (saaa/{app_id}/{archivo_id}/{nombre}),
        retorna la URL del proxy Django en lugar de la URL local.
        Usa resolve_public_url() para respetar FILE_PROXY_URL (absoluto o relativo).
        """
        url = resolve_public_url(
            archivo_field_name=archivo.archivo.name if archivo.archivo else "",
            archivo_url_attr=archivo.archivo,
        )

        return ExpedienteArchivoOut(
            id=archivo.id,
            tipo_archivo=archivo.tipo_archivo,
            nombre_original=archivo.nombre_original,
            url=url,
        )
