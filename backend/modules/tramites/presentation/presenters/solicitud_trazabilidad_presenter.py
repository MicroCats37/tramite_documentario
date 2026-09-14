"""
SolicitudTrazabilidadPresenter — pure transformer for the traceability endpoint.

No DB calls. Receives a fully-eager-loaded Solicitud domain object
and maps it to SolicitudTrazabilidadOut.
"""
from datetime import datetime

from modules.tramites.domain.models.solicitud import Solicitud
from modules.tramites.presentation.schemas.solicitud_trazabilidad_out import (
    SolicitudTrazabilidadOut,
    HistorialEstadoGlobalOut,
    AsignacionTrazabilidadOut,
    PeriodoTrazabilidadOut,
    PeriodoEstadoHistorialOut,
    ParticipanteTrazabilidadOut,
    RespuestaTrazabilidadOut,
    TimelineEventOut,
)


def _full_name(user) -> str | None:
    """Build full name from a user model instance; returns None if user is None."""
    if user is None:
        return None
    return f"{user.nombres or ''} {user.apellidos or ''}".strip()


class SolicitudTrazabilidadPresenter:
    """Pure presenter: Solicitud domain object → SolicitudTrazabilidadOut schema."""

    @staticmethod
    def _build_timeline(solicitud: Solicitud) -> list[TimelineEventOut]:
        """Build chronological timeline from the eager-loaded graph."""
        events: list[tuple[datetime, TimelineEventOut]] = []

        for h in sorted(solicitud.historial_estados.all(), key=lambda x: x.fecha_cambio):
            events.append((h.fecha_cambio, TimelineEventOut(
                timestamp=h.fecha_cambio,
                tipo="ESTADO_SOLICITUD",
                descripcion=f"Estado cambió a {h.estado_nuevo}",
                actor_nombres=_full_name(h.cambiado_por),
                actor_id=h.cambiado_por.id if h.cambiado_por else None,
                event_estado_anterior=h.estado_anterior,
                event_estado_nuevo=h.estado_nuevo,
            )))

        for asignacion in sorted(solicitud.asignaciones.all(), key=lambda a: a.fecha_incorporacion):
            events.append((asignacion.fecha_incorporacion, TimelineEventOut(
                timestamp=asignacion.fecha_incorporacion,
                tipo="AREA_INCORPORADA",
                descripcion=f"Área {asignacion.area.nombre} incorporada",
                actor_nombres=_full_name(asignacion.incorporado_por),
                actor_id=asignacion.incorporado_por.id if asignacion.incorporado_por else None,
                event_area_id=asignacion.area.id,
            )))

            for periodo in sorted(asignacion.periodos.all(), key=lambda p: p.numero_ciclo):
                events.append((periodo.fecha_inicio, TimelineEventOut(
                    timestamp=periodo.fecha_inicio,
                    tipo="PERIODO_INICIADO",
                    descripcion=f"Período ciclo {periodo.numero_ciclo} ({periodo.tipo_participacion}) iniciado",
                    actor_nombres=_full_name(periodo.iniciado_por),
                    actor_id=periodo.iniciado_por.id if periodo.iniciado_por else None,
                    event_area_id=asignacion.area.id,
                    event_periodo_id=periodo.id,
                )))

                for part in periodo.usuarios.all():
                    events.append((part.fecha_inicio, TimelineEventOut(
                        timestamp=part.fecha_inicio,
                        tipo="PARTICIPANTE_AGREGADO",
                        descripcion=f"Participante {part.usuario.nombres} {part.usuario.apellidos} agregado ({part.rol or 'sin rol'})",
                        actor_nombres=_full_name(part.asignado_por),
                        actor_id=part.asignado_por.id if part.asignado_por else None,
                        event_area_id=asignacion.area.id,
                        event_periodo_id=periodo.id,
                        event_participante_id=part.usuario.id,
                    )))
                    if part.fecha_fin:
                        events.append((part.fecha_fin, TimelineEventOut(
                            timestamp=part.fecha_fin,
                            tipo="PARTICIPANTE_RETIRO",
                            descripcion=f"Participante {part.usuario.nombres} {part.usuario.apellidos} retirado",
                            actor_nombres=_full_name(part.retirado_por),
                            actor_id=part.retirado_por.id if part.retirado_por else None,
                            event_area_id=asignacion.area.id,
                            event_periodo_id=periodo.id,
                            event_participante_id=part.usuario.id,
                        )))

                for resp in periodo.respuestas.all():
                    if resp.fecha_emision:
                        events.append((resp.fecha_emision, TimelineEventOut(
                            timestamp=resp.fecha_emision,
                            tipo="RESPUESTA_EMITIDA",
                            descripcion=f"Respuesta {resp.tipo_respuesta} emitida",
                            actor_nombres=_full_name(resp.emitido_por),
                            actor_id=resp.emitido_por.id if resp.emitido_por else None,
                            event_area_id=asignacion.area.id,
                            event_periodo_id=periodo.id,
                            event_respuesta_id=resp.id,
                        )))

                if periodo.fecha_fin:
                    events.append((periodo.fecha_fin, TimelineEventOut(
                        timestamp=periodo.fecha_fin,
                        tipo="PERIODO_CERRADO",
                        descripcion=f"Período ciclo {periodo.numero_ciclo} cerrado ({periodo.tipo_cierre or 'sin tipo'})",
                        actor_nombres=_full_name(periodo.finalizado_por),
                        actor_id=periodo.finalizado_por.id if periodo.finalizado_por else None,
                        event_area_id=asignacion.area.id,
                        event_periodo_id=periodo.id,
                    )))

        def sort_key(item: tuple[datetime, TimelineEventOut]) -> tuple:
            return (item[0].isoformat() if item[0] else "", item[1].tipo, item[1].descripcion)

        events.sort(key=sort_key)
        return [event for _, event in events]

    @staticmethod
    def _build_periodo_historial(historial_qs) -> list[PeriodoEstadoHistorialOut]:
        return [
            PeriodoEstadoHistorialOut(
                estado_anterior=h.estado_anterior,
                estado_nuevo=h.estado_nuevo,
                fecha_cambio=h.fecha_cambio,
                cambiado_por_id=h.cambiado_por.id if h.cambiado_por else None,
                cambiado_por_nombres=_full_name(h.cambiado_por),
                origen=h.origen,
                motivo=h.motivo,
            )
            for h in sorted(historial_qs.all(), key=lambda x: x.fecha_cambio)
        ]

    @staticmethod
    def _build_participantes(usuarios_qs) -> list[ParticipanteTrazabilidadOut]:
        return [
            ParticipanteTrazabilidadOut(
                usuario_id=u.usuario.id,
                usuario_nombres=_full_name(u.usuario),
                rol=u.rol,
                fecha_inicio=u.fecha_inicio,
                fecha_fin=u.fecha_fin,
                activo=u.fecha_fin is None,
                asignado_por_id=u.asignado_por.id if u.asignado_por else None,
                asignado_por_nombres=_full_name(u.asignado_por),
                retirado_por_id=u.retirado_por.id if u.retirado_por else None,
                retirado_por_nombres=_full_name(u.retirado_por),
                motivo_retiro=u.motivo_retiro,
            )
            for u in usuarios_qs.all()
        ]

    @staticmethod
    def _build_respuestas(respuestas_qs) -> list[RespuestaTrazabilidadOut]:
        return [
            RespuestaTrazabilidadOut(
                id=r.id,
                tipo_respuesta=r.tipo_respuesta,
                contenido=r.contenido,
                estado=r.estado,
                fecha_emision=r.fecha_emision,
                emitido_por_id=r.emitido_por.id if r.emitido_por else None,
                emitido_por_nombres=_full_name(r.emitido_por),
            )
            for r in respuestas_qs.all()
        ]

    @staticmethod
    def _build_periodos(periodos_qs) -> list[PeriodoTrazabilidadOut]:
        return [
            PeriodoTrazabilidadOut(
                id=p.id,
                numero_ciclo=p.numero_ciclo,
                tipo_participacion=p.tipo_participacion,
                estado=p.estado,
                fecha_inicio=p.fecha_inicio,
                fecha_fin=p.fecha_fin,
                tipo_cierre=p.tipo_cierre,
                iniciado_por_id=p.iniciado_por.id if p.iniciado_por else None,
                iniciado_por_nombres=_full_name(p.iniciado_por),
                finalizado_por_id=p.finalizado_por.id if p.finalizado_por else None,
                finalizado_por_nombres=_full_name(p.finalizado_por),
                motivo_cierre=p.motivo_cierre,
                historial_estados=SolicitudTrazabilidadPresenter._build_periodo_historial(p.historial_estados),
                participantes=SolicitudTrazabilidadPresenter._build_participantes(p.usuarios),
                respuestas=SolicitudTrazabilidadPresenter._build_respuestas(p.respuestas),
            )
            for p in sorted(periodos_qs.all(), key=lambda x: x.numero_ciclo)
        ]

    @staticmethod
    def _build_asignaciones(asignaciones_qs) -> list[AsignacionTrazabilidadOut]:
        return [
            AsignacionTrazabilidadOut(
                id=a.id,
                area_id=a.area.id,
                area_nombre=a.area.nombre,
                bloquea_cierre=a.bloquea_cierre,
                fecha_incorporacion=a.fecha_incorporacion,
                incorporado_por_id=a.incorporado_por.id if a.incorporado_por else None,
                incorporado_por_nombres=_full_name(a.incorporado_por),
                observacion=a.observacion,
                tipo_actual=sorted(a.periodos.all(), key=lambda x: x.numero_ciclo)[-1].tipo_participacion if a.periodos.exists() else None,
                etapas=SolicitudTrazabilidadPresenter._build_periodos(a.periodos),
            )
            for a in asignaciones_qs.all()
        ]

    @staticmethod
    def _build_historial_global(historial_qs) -> list[HistorialEstadoGlobalOut]:
        return [
            HistorialEstadoGlobalOut(
                estado_anterior=h.estado_anterior,
                estado_nuevo=h.estado_nuevo,
                fecha_cambio=h.fecha_cambio,
                cambiado_por_id=h.cambiado_por.id,
                cambiado_por_nombres=_full_name(h.cambiado_por),
                origen=h.origen,
                observacion=h.observacion,
            )
            for h in sorted(historial_qs.all(), key=lambda x: x.fecha_cambio)
        ]

    @classmethod
    def present_trazabilidad(cls, solicitud: Solicitud) -> SolicitudTrazabilidadOut:
        return SolicitudTrazabilidadOut(
            solicitud_id=solicitud.id,
            historial_estados=cls._build_historial_global(solicitud.historial_estados),
            areas=cls._build_asignaciones(solicitud.asignaciones),
            timeline=cls._build_timeline(solicitud),
        )
