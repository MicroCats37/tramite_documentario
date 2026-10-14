"""
ExpedienteConsultaPresenter — transforma datos de consulta de Expediente a esquemas HTTP.

Extrae la lógica de presentación de ExpedienteController.listar_expedientes y
obtener_expediente, siguiendo el contrato de controllers-delgados (薄).
"""
from uuid import UUID

from modules.tramites.domain.models.expediente import Expediente
from modules.tramites.domain.constants import TipoPersona
from modules.tramites.presentation.presenters.archivo_presenter import map_archivo_to_out
from modules.tramites.presentation.schemas.expediente_out import ExpedienteArchivoOut
from modules.tramites.presentation.schemas.expediente_list_out import (
    ExpedienteItemOut,
    ExpedienteDetailOut,
    ExpedienteAntecedenteOut,
)


class ExpedienteConsultaPresenter:
    """
    Presenter para consultas (listado y detalle) de Expediente.

    Mantiene la forma de la respuesta JSON - solo mueve la construcción
    de los schemas Out desde el controller hacia acá.
    """

    @staticmethod
    def present_list_item(expediente: Expediente) -> ExpedienteItemOut:
        """
        Construye un ExpedienteItemOut desde una entidad Expediente (listado).

        Incluye archivos con URL para cache en frontend.
        Phase 1: populates both legacy flat fields AND nested `archivo` object.

        Args:
            expediente: Entidad Expediente

        Returns:
            ExpedienteItemOut listo para PaginatedData
        """
        archivos = []
        for a in expediente.archivos.all():
            archivo_out = map_archivo_to_out(a.archivo) if a.archivo else None
            archivos.append(
                ExpedienteArchivoOut(
                    id=a.id,
                    tipo_archivo=a.tipo_archivo,
                    nombre_original=a.archivo.nombre_original if a.archivo else "",
                    url=archivo_out.url if archivo_out else "",
                    archivo=archivo_out,
                )
            )

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
            tipo_documento=expediente.tipo_documento,
            numero_documento=expediente.numero_documento,
            numero_folios=expediente.numero_folios,
            asunto=expediente.asunto,
            observaciones=expediente.observaciones,
            fecha_registro=expediente.fecha_registro,
            archivos=archivos,
        )

    @staticmethod
    def present_list_items(expedientes: list[Expediente]) -> list[ExpedienteItemOut]:
        """
        Construye una lista de ExpedienteItemOut (listado paginado).

        Args:
            expedientes: Lista de entidades Expediente

        Returns:
            Lista de ExpedienteItemOut
        """
        return [
            ExpedienteConsultaPresenter.present_list_item(exp)
            for exp in expedientes
        ]

    @staticmethod
    def present_detail(expediente: Expediente) -> ExpedienteDetailOut:
        """
        Construye un ExpedienteDetailOut desde una entidad Expediente (detalle).

        Incluye archivos, antecedentes, datos del creador y solicitud asociada (si existe).

        Args:
            expediente: Entidad Expediente con relaciones eager-loaded

        Returns:
            ExpedienteDetailOut listo para respuesta HTTP
        """
        # Archivos
        archivos = []
        for a in expediente.archivos.all():
            archivo_out = map_archivo_to_out(a.archivo) if a.archivo else None
            archivos.append(
                ExpedienteArchivoOut(
                    id=a.id,
                    tipo_archivo=a.tipo_archivo,
                    nombre_original=a.archivo.nombre_original if a.archivo else "",
                    url=archivo_out.url if archivo_out else "",
                    archivo=archivo_out,
                )
            )

        # Antecedentes
        antecedentes = [
            ExpedienteAntecedenteOut(
                id_publico=a.antecedente.id_publico,
                categoria=a.categoria,
                observaciones=a.observaciones,
            )
            for a in expediente.antecedentes_vinculados.all()
        ]

        # Creado por
        creado_por_nombres = None
        if expediente.creado_por:
            creado_por_nombres = f"{expediente.creado_por.nombres or ''} {expediente.creado_por.apellidos or ''}".strip()

        # Solicitud asociada (1:1)
        # The relation is already eager loaded via select_related("solicitud") in the orchestrator
        solicitud_id = None
        solicitud_estado = None
        solicitud_prioridad = None
        try:
            solicitud = expediente.solicitud
            if solicitud:
                solicitud_id = solicitud.id
                solicitud_estado = solicitud.estado
                solicitud_prioridad = solicitud.prioridad
        except AttributeError:
            pass

        return ExpedienteDetailOut(
            id=expediente.id,
            numero=expediente.numero,
            id_publico=expediente.id_publico,
            tipo_persona=expediente.tipo_persona,
            dni=expediente.dni,
            ruc=expediente.ruc,
            cip=expediente.cip,
            razon_social=expediente.razon_social,
            nombres=expediente.nombres,
            apellidos=expediente.apellidos,
            correo=expediente.correo,
            telefono=expediente.telefono,
            tipo_documento=expediente.tipo_documento,
            numero_documento=expediente.numero_documento,
            numero_folios=expediente.numero_folios,
            asunto=expediente.asunto,
            observaciones=expediente.observaciones,
            fecha_registro=expediente.fecha_registro,
            archivos=archivos,
            antecedentes=antecedentes,
            creado_por_nombres=creado_por_nombres,
            solicitud_id=solicitud_id,
            solicitud_estado=solicitud_estado,
            solicitud_prioridad=solicitud_prioridad,
        )
