"""
SolicitudConsultaPresenter — transforma datos de consulta de Solicitud a esquemas HTTP.

Extrae la lógica de presentación de SolicitudController.listar_solicitudes y
obtener_solicitud, siguiendo el contrato de controllers-delgados (薄).
"""
from uuid import UUID

from modules.tramites.domain.models.solicitud import Solicitud
from modules.tramites.domain.models.expediente import Expediente
from modules.tramites.presentation.schemas.solicitud_list_out import (
    SolicitudItemOut,
    SolicitudDetailOut,
    AreaActivaOut,
    AsignacionDetalleOut,
    PeriodoDetalleOut,
    ParticipanteDetalleOut,
    RespuestaDetalleOut,
    HistorialEstadoGlobalOut,
)
from modules.tramites.presentation.schemas.expediente_out import ExpedienteArchivoOut
from modules.tramites.presentation.schemas.expediente_list_out import ExpedienteItemOut, ExpedienteDetailOut, ExpedienteAntecedenteOut


class SolicitudConsultaPresenter:
    """
    Presenter para consultas (listado y detalle) de Solicitud.

    Mantiene la forma de la respuesta JSON - solo mueve la construcción
    de los schemas Out desde el controller hacia acá.
    """

    @staticmethod
    def present_list_item(solicitud: Solicitud) -> SolicitudItemOut:
        """
        Construye un SolicitudItemOut desde una entidad Solicitud (listado).

        Incluye expediente anidado con archivos para reutilización en frontend.

        Args:
            solicitud: Entidad Solicitud con expediente y asignaciones eager-loaded

        Returns:
            SolicitudItemOut listo para PaginatedData
        """
        exp = solicitud.expediente

        # Build nested expediente with archivos
        exp_archivos = [
            ExpedienteArchivoOut(
                id=a.id,
                tipo_archivo=a.tipo_archivo,
                nombre_original=a.nombre_original,
                url=a.archivo.url if a.archivo else "",
            )
            for a in exp.archivos.all()
        ]

        expediente_out = ExpedienteItemOut(
            id=exp.id,
            id_publico=exp.id_publico,
            numero=exp.numero,
            tipo_persona=exp.tipo_persona,
            dni=exp.dni,
            ruc=exp.ruc,
            cip=exp.cip,
            razon_social=exp.razon_social,
            nombres=exp.nombres,
            apellidos=exp.apellidos,
            correo=exp.correo,
            telefono=exp.telefono,
            tipo_documento=exp.tipo_documento,
            numero_documento=exp.numero_documento,
            numero_folios=exp.numero_folios,
            asunto=exp.asunto,
            observaciones=exp.observaciones,
            fecha_registro=exp.fecha_registro,
            archivos=exp_archivos,
        )

        # Construir áreas activas y conteos
        areas_activas = []
        conteo_pendiente = 0
        conteo_en_gestion = 0

        from modules.asignaciones.domain.constants import EstadoPeriodo

        for asignacion in solicitud.asignaciones.all():
            area = asignacion.area
            periodos = list(asignacion.periodos.all())
            if not periodos:
                continue

            # Último período
            ultimo = max(periodos, key=lambda p: p.numero_ciclo)

            areas_activas.append(AreaActivaOut(
                area_id=area.id,
                area_nombre=area.nombre,
                tipo_participacion=ultimo.tipo_participacion,
                estado_periodo=ultimo.estado,
            ))

            if ultimo.estado == EstadoPeriodo.PENDIENTE:
                conteo_pendiente += 1
            elif ultimo.estado == EstadoPeriodo.EN_GESTION:
                conteo_en_gestion += 1

        return SolicitudItemOut(
            id=solicitud.id,
            expediente=expediente_out,
            estado=solicitud.estado,
            prioridad=solicitud.prioridad,
            fecha_registro=solicitud.fecha_registro,
            fecha_inicio_gestion=solicitud.fecha_inicio_gestion,
            fecha_limite=solicitud.fecha_limite,
            areas_activas=areas_activas,
            conteo_pendiente=conteo_pendiente,
            conteo_en_gestion=conteo_en_gestion,
        )

    @staticmethod
    def present_detail(solicitud: Solicitud) -> SolicitudDetailOut:
        """
        Construye un SolicitudDetailOut desde una entidad Solicitud (detalle).

        Consolida expediente con archivos y antecedentes, historial global,
        y todas las asignaciones con períodos, participantes y respuestas.

        Args:
            solicitud: Entidad Solicitud con todas las relaciones eager-loaded

        Returns:
            SolicitudDetailOut listo para respuesta HTTP
        """
        exp = solicitud.expediente

        # Expediente con archivos y antecedentes
        exp_archivos = list(exp.archivos.all())
        exp_antecedentes = list(exp.antecedentes_vinculados.all())

        # Build archivos with url
        archivos_out = [
            ExpedienteArchivoOut(
                id=a.id,
                tipo_archivo=a.tipo_archivo,
                nombre_original=a.nombre_original,
                url=a.archivo.url if a.archivo else "",
            )
            for a in exp_archivos
        ]

        # Build antecedentes
        antecedentes_out = [
            ExpedienteAntecedenteOut(
                id_publico=a.antecedente.id_publico,
                categoria=a.categoria,
                observaciones=a.observaciones,
            )
            for a in exp_antecedentes
        ]

        # Creado por
        creado_por_nombres = None
        if exp.creado_por:
            creado_por_nombres = f"{exp.creado_por.nombres or ''} {exp.creado_por.apellidos or ''}".strip()

        # Solicitud asociada
        solicitud_id = None
        solicitud_estado = None
        solicitud_prioridad = None
        try:
            if exp.solicitud:
                solicitud_id = exp.solicitud.id
                solicitud_estado = exp.solicitud.estado
                solicitud_prioridad = exp.solicitud.prioridad
        except AttributeError:
            pass

        expediente_out = ExpedienteDetailOut(
            id=exp.id,
            numero=exp.numero,
            id_publico=exp.id_publico,
            tipo_persona=exp.tipo_persona,
            dni=exp.dni,
            ruc=exp.ruc,
            cip=exp.cip,
            razon_social=exp.razon_social,
            nombres=exp.nombres,
            apellidos=exp.apellidos,
            correo=exp.correo,
            telefono=exp.telefono,
            tipo_documento=exp.tipo_documento,
            numero_documento=exp.numero_documento,
            numero_folios=exp.numero_folios,
            asunto=exp.asunto,
            observaciones=exp.observaciones,
            fecha_registro=exp.fecha_registro,
            archivos=archivos_out,
            antecedentes=antecedentes_out,
            creado_por_nombres=creado_por_nombres,
            solicitud_id=solicitud_id,
            solicitud_estado=solicitud_estado,
            solicitud_prioridad=solicitud_prioridad,
        )

        # Historial global de estados
        historial_global = [
            {
                "estado_anterior": h.estado_anterior,
                "estado_nuevo": h.estado_nuevo,
                "fecha_cambio": h.fecha_cambio,
                "cambiado_por_nombres": f"{h.cambiado_por.nombres or ''} {h.cambiado_por.apellidos or ''}".strip(),
                "origen": h.origen,
                "observacion": h.observacion,
            }
            for h in sorted(solicitud.historial_estados.all(), key=lambda x: x.fecha_cambio)
        ]

        # Asignaciones con detalle
        asignaciones_out = []
        for asignacion in solicitud.asignaciones.all():
            area = asignacion.area

            # Períodos ordenados por ciclo
            periodos = sorted(asignacion.periodos.all(), key=lambda p: p.numero_ciclo)
            periodos_out = []
            for periodo in periodos:
                historial_periodo = [
                    {
                        "estado": h.estado,
                        "fecha_cambio": h.fecha_cambio.isoformat() if h.fecha_cambio else None,
                        "origen": h.origen,
                    }
                    for h in sorted(periodo.historial_estados.all(), key=lambda x: x.fecha_cambio)
                ]

                participantes_out = [
                    {
                        "usuario_id": part.usuario.id,
                        "usuario_nombres": f"{part.usuario.nombres or ''} {part.usuario.apellidos or ''}".strip(),
                        "rol": part.rol,
                        "fecha_inicio": part.fecha_inicio,
                        "fecha_fin": part.fecha_fin,
                        "activo": part.fecha_fin is None,
                    }
                    for part in periodo.usuarios.all()
                ]

                respuestas_out = []
                for resp in periodo.respuestas.all():
                    emitido_por_nombres = None
                    if resp.emitido_por:
                        emitido_por_nombres = f"{resp.emitido_por.nombres or ''} {resp.emitido_por.apellidos or ''}".strip()
                    respuestas_out.append({
                        "id": resp.id,
                        "tipo_respuesta": resp.tipo_respuesta,
                        "contenido": resp.contenido,
                        "estado": resp.estado,
                        "fecha_emision": resp.fecha_emision,
                        "emitido_por_nombres": emitido_por_nombres,
                    })

                periodos_out.append({
                    "id": periodo.id,
                    "numero_ciclo": periodo.numero_ciclo,
                    "tipo_participacion": periodo.tipo_participacion,
                    "estado": periodo.estado,
                    "fecha_inicio": periodo.fecha_inicio,
                    "fecha_fin": periodo.fecha_fin,
                    "tipo_cierre": periodo.tipo_cierre,
                    "iniciado_por_nombres": f"{periodo.iniciado_por.nombres or ''} {periodo.iniciado_por.apellidos or ''}".strip() if periodo.iniciado_por else None,
                    "historial_estados": historial_periodo,
                })

            participantes_out = [
                {
                    "usuario_id": part.usuario.id,
                    "usuario_nombres": f"{part.usuario.nombres or ''} {part.usuario.apellidos or ''}".strip(),
                    "rol": part.rol,
                    "fecha_inicio": part.fecha_inicio,
                    "fecha_fin": part.fecha_fin,
                    "activo": part.fecha_fin is None,
                }
                for part in periodo.usuarios.all()
            ]

            respuestas_out = []
            for resp in periodo.respuestas.all():
                emitido_por_nombres = None
                if resp.emitido_por:
                    emitido_por_nombres = f"{resp.emitido_por.nombres or ''} {resp.emitido_por.apellidos or ''}".strip()
                respuestas_out.append({
                    "id": resp.id,
                    "tipo_respuesta": resp.tipo_respuesta,
                    "contenido": resp.contenido,
                    "estado": resp.estado,
                    "fecha_emision": resp.fecha_emision,
                    "emitido_por_nombres": emitido_por_nombres,
                })

            asignaciones_out.append({
                "id": asignacion.id,
                "area_id": area.id,
                "area_nombre": area.nombre,
                "bloquea_cierre": asignacion.bloquea_cierre,
                "fecha_incorporacion": asignacion.fecha_incorporacion,
                "observacion": asignacion.observacion,
                "periodos": periodos_out,
                "participantes": participantes_out,
                "respuestas": respuestas_out,
            })

        return SolicitudDetailOut(
            id=solicitud.id,
            estado=solicitud.estado,
            prioridad=solicitud.prioridad,
            fecha_registro=solicitud.fecha_registro,
            fecha_inicio_gestion=solicitud.fecha_inicio_gestion,
            fecha_limite=solicitud.fecha_limite,
            fecha_cierre=solicitud.fecha_cierre,
            observacion=solicitud.observacion,
            expediente=expediente_out,
            historial_global=historial_global,
            asignaciones=asignaciones_out,
        )
