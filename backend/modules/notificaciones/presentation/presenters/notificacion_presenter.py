"""
NotificacionPresenter — transforma datos de consulta de Notificacion a esquemas HTTP.

Extrae la lógica de presentación de NotificacionController.listar_notificaciones y
obtener_notificacion, siguiendo el contrato de controllers-delgados (薄).
"""
from uuid import UUID

from modules.notificaciones.domain.models import Notificacion, NotificacionUsuario
from modules.notificaciones.presentation.schemas.notificacion_schemas import (
    NotificacionListItemOut,
    NotificacionItemOut,
    NotificacionDetailOut,
    NotificacionDetalleOut,
    ExpedientePublicoOut,
    PeriodoContextOut,
    InteraccionOut,
    EstadoIndividual,
)


class NotificacionPresenter:
    """
    Presenter para consultas (listado y detalle) de Notificacion.

    Mantiene la forma de la respuesta JSON - solo mueve la construcción
    de los schemas Out desde el controller hacia acá.
    """

    @staticmethod
    def _compute_estado_individual(interaccion) -> EstadoIndividual:
        """Deriva el estado individual desde la interacción del usuario."""
        if interaccion is None:
            return EstadoIndividual.NO_VISTA
        if interaccion.descartada_at is not None:
            return EstadoIndividual.DESCARTADA
        if interaccion.abierta_at is not None:
            return EstadoIndividual.ABIERTA
        if interaccion.vista_at is not None:
            return EstadoIndividual.VISTA
        return EstadoIndividual.NO_VISTA

    @staticmethod
    def _compute_audiencia_tipo(notif: Notificacion) -> str | None:
        """
        Deriva el tipo de audiencia desde las relaciones cargadas.
        
        Computed output only — NOT persisted on Notificacion.
        Returns 'AREA' if NotificacionArea relations exist, 'USUARIO' if only NotificacionUsuario.
        """
        # Check if there are any NotificacionArea records
        if hasattr(notif, "areas_notificadas") and notif.areas_notificadas.exists():
            return "AREA"
        # Otherwise it's user-directed
        return "USUARIO"

    @staticmethod
    def _compute_participo(notif: Notificacion, usuario_id: int):
        """
        Deriva si el usuario participó en el período/notificación.

        Returns True/False si se puede determinar, None si no se puede determinar
        (e.g., no hay contexto de asignación cargado).
        """
        # Guard: avoid triggering Django lazy-loaded descriptors in async context.
        # Check fields_cache directly — NEVER use hasattr() on FK descriptors
        # as it invokes the descriptor and can raise SynchronousOnlyOperation.
        if "asignacion" not in notif._state.fields_cache:
            # Not prefetched — accessing it would trigger a sync DB query.
            # Return None to stay safe in async contexts; caller gets safe default.
            return None
        asignacion = notif.asignacion
        if not asignacion:
            return False
        # Check if user is in SolicitudAsignacionUsuario for any period of this asignacion
        for periodo in asignacion.periodos.all():
            for asignacion_usuario in periodo.usuarios.all():
                if asignacion_usuario.usuario_id == usuario_id:
                    return True
        return False

    @staticmethod
    def _get_solicitud_context(notif: Notificacion):
        """
        Get solicitud_id, expediente_id_publico, solicitud_asunto from loaded contexto_solicitud relation.
        
        Returns tuple (solicitud_id, expediente_id_publico, solicitud_asunto).
        Returns (None, None, None) if no contexto_solicitud is prefetched or empty.
        """
        if not hasattr(notif, "_prefetched_objects_cache") or \
           "contexto_solicitud" not in notif._prefetched_objects_cache:
            return None, None, None
        
        contexto_list = notif._prefetched_objects_cache.get("contexto_solicitud")
        if not contexto_list:
            return None, None, None
        
        contexto = contexto_list[0]  # UniqueConstraint ensures only one
        solicitud = getattr(contexto, "solicitud", None)
        if not solicitud:
            return None, None, None
        
        solicitud_id = solicitud.id
        expediente_id_publico = None
        solicitud_asunto = None
        if hasattr(solicitud, "expediente") and solicitud.expediente:
            expediente_id_publico = solicitud.expediente.id_publico
            solicitud_asunto = solicitud.expediente.asunto
        
        return solicitud_id, expediente_id_publico, solicitud_asunto

    @staticmethod
    def _get_periodo_context(notif: Notificacion):
        """
        Get periodo_id, periodo_ciclo, periodo_activo from loaded contexto_solicitud relation.
        
        Returns tuple (periodo_id, periodo_ciclo, periodo_activo).
        Returns (None, None, None) if no periodo in contexto_solicitud.
        """
        if not hasattr(notif, "_prefetched_objects_cache") or \
           "contexto_solicitud" not in notif._prefetched_objects_cache:
            return None, None, None
        
        contexto_list = notif._prefetched_objects_cache.get("contexto_solicitud")
        if not contexto_list:
            return None, None, None
        
        contexto = contexto_list[0]
        periodo = getattr(contexto, "periodo", None)
        if not periodo:
            return None, None, None
        
        return periodo.id, getattr(periodo, "numero_ciclo", None), getattr(periodo, "esta_abierto", None)

    @staticmethod
    def present_list_item(
        notif: Notificacion,
        usuario_id: int,
    ) -> NotificacionListItemOut:
        """
        Construye un NotificacionListItemOut desde una entidad Notificacion (listado).

        Retorna únicamente campos comunes — los campos contextuales
        (solicitud_id, expediente_id_publico, area_nombre, periodo_id,
        solicitud_asunto, periodo_ciclo, periodo_activo, participo, audiencia_tipo)
        se obtienen via GET /api/notificaciones/{id}/detalle.

        Args:
            notif: Entidad Notificacion con usuarios_notificados prefetched
            usuario_id: ID del usuario autenticado (para buscar su interacción)

        Returns:
            NotificacionListItemOut listo para PaginatedData
        """
        # Obtener la interacción del usuario actual (ya prefetched)
        interacciones_usuario = [
            iu for iu in notif.usuarios_notificados.all()
            if iu.usuario_id == usuario_id
        ]
        interaccion = interacciones_usuario[0] if interacciones_usuario else None

        vista = interaccion.vista_at is not None if interaccion else False
        abierta = interaccion.abierta_at is not None if interaccion else False
        descartada = interaccion.descartada_at is not None if interaccion else False
        interactuada = vista or abierta or descartada

        # Estado individual
        estado_individual = NotificacionPresenter._compute_estado_individual(interaccion)

        return NotificacionListItemOut(
            id=notif.id,
            ambito=notif.ambito,
            evento=notif.evento,
            prioridad=notif.prioridad,
            titulo=notif.titulo,
            mensaje=notif.mensaje,
            ocurrido_en=notif.ocurrido_en,
            interactuada=interactuada,
            vista=vista,
            abierta=abierta,
            descartada=descartada,
            estado_individual=estado_individual,
        )

    @staticmethod
    def present_detail(
        notif: Notificacion,
        usuario_id: int,
    ) -> NotificacionDetailOut:
        """
        Construye un NotificacionDetailOut desde una entidad Notificacion (detalle).

        Incluye contexto (solicitud, expediente, área, período) e interacciones
        del usuario autenticado.

        Args:
            notif: Entidad Notificacion con relaciones eager-loaded
            usuario_id: ID del usuario autenticado

        Returns:
            NotificacionDetailOut listo para respuesta HTTP
        """
        # Contexto — área derivada de NotificacionArea (no de Notificacion.area FK)
        areas_list = list(notif.areas_notificadas.all()) if hasattr(notif, "areas_notificadas") else []
        area_obj = areas_list[0] if areas_list else None
        area_id = area_obj.area_id if area_obj else None
        area_nombre = area_obj.area.nombre if area_obj else None

        # Obtener contexto de solicitud desde link table
        solicitud_id, expediente_id_publico, solicitud_asunto = NotificacionPresenter._get_solicitud_context(notif)
        expediente_asunto = solicitud_asunto  # same source

        # Obtener contexto de periodo desde link table
        periodo_id, periodo_ciclo, periodo_activo = NotificacionPresenter._get_periodo_context(notif)

        # Generada por
        generada_por_nombres = None
        if notif.generada_por:
            generada_por_nombres = f"{notif.generada_por.nombres or ''} {notif.generada_por.apellidos or ''}".strip()

        # Interacciones del usuario actual (sobre relación prefetched — sin BD extra)
        iu_qs = [iu for iu in notif.usuarios_notificados.all() if iu.usuario_id == usuario_id]
        interacciones = [
            InteraccionOut(
                usuario_id=iu.usuario_id,
                vista_at=iu.vista_at,
                abierta_at=iu.abierta_at,
                descartada_at=iu.descartada_at,
            )
            for iu in iu_qs
        ]

        # Interaccion del usuario para estado individual
        interaccion = iu_qs[0] if iu_qs else None

        # Computed: audiencia_tipo
        audiencia_tipo = NotificacionPresenter._compute_audiencia_tipo(notif)

        # Estado individual
        estado_individual = NotificacionPresenter._compute_estado_individual(interaccion)

        # Participo (requires asignacion context)
        participo = NotificacionPresenter._compute_participo(notif, usuario_id)

        return NotificacionDetailOut(
            id=notif.id,
            ambito=notif.ambito,
            evento=notif.evento,
            prioridad=notif.prioridad,
            titulo=notif.titulo,
            mensaje=notif.mensaje,
            ocurrido_en=notif.ocurrido_en,
            generada_por_nombres=generada_por_nombres,
            area_id=area_id,
            area_nombre=area_nombre,
            solicitud_id=solicitud_id,
            expediente_id_publico=expediente_id_publico,
            expediente_asunto=expediente_asunto,
            periodo_id=periodo_id,
            interacciones=interacciones,
            audiencia_tipo=audiencia_tipo,
            estado_individual=estado_individual,
            solicitud_asunto=solicitud_asunto,
            periodo_ciclo=periodo_ciclo,
            periodo_activo=periodo_activo,
            participo=participo,
        )

    # ── Detail contextual con restructure (nuevos endpoints) ───────────────────

    AMBITO_PRESENTER_MAP = {
        "SOLICITUD": "present_detail_solicitud",
    }
    """Mapa de dispatch por ámbito. Agregar nuevas entradas cuando lleguen nuevos ámbitos."""

    @staticmethod
    def present_detail_contextual(
        notif: Notificacion,
        usuario_id: int,
    ) -> NotificacionDetalleOut:
        """
        Construye un NotificacionDetalleOut con dispatch por ámbito.

        Utiliza present_detail_solicitud para SOLICITUD y present_detail_base
        como fallback para otros ámbitos (ej. SISTEMA).

        Args:
            notif: Entidad Notificacion con relaciones eager-loaded
            usuario_id: ID del usuario autenticado

        Returns:
            NotificacionDetalleOut con contexto apropiado según el ámbito
        """
        handler_name = NotificacionPresenter.AMBITO_PRESENTER_MAP.get(notif.ambito)
        if handler_name == "present_detail_solicitud":
            return NotificacionPresenter.present_detail_solicitud(notif, usuario_id)
        return NotificacionPresenter.present_detail_base(notif, usuario_id)

    @staticmethod
    def present_detail_solicitud(
        notif: Notificacion,
        usuario_id: int,
    ) -> NotificacionDetalleOut:
        """
        Construye un NotificacionDetalleOut para notificaciones de ámbito SOLICITUD.

        Transforma campos planos del expediente y período en objetos anidados
        (expediente_publico, periodo) según el contrato de detalle combinado.

        Args:
            notif: Entidad Notificacion con relaciones eager-loaded
            usuario_id: ID del usuario autenticado

        Returns:
            NotificacionDetalleOut con expediente_publico y periodo anidados
        """
        # Interacciones del usuario actual
        iu_qs = [
            iu for iu in notif.usuarios_notificados.all()
            if iu.usuario_id == usuario_id
        ]
        interacciones = [
            InteraccionOut(
                usuario_id=iu.usuario_id,
                vista_at=iu.vista_at,
                abierta_at=iu.abierta_at,
                descartada_at=iu.descartada_at,
            )
            for iu in iu_qs
        ]
        interaccion = iu_qs[0] if iu_qs else None

        # Área desde NotificacionArea
        areas_list = (
            list(notif.areas_notificadas.all())
            if hasattr(notif, "areas_notificadas")
            else []
        )
        area_obj = areas_list[0] if areas_list else None
        area_id = area_obj.area_id if area_obj else None
        area_nombre = area_obj.area.nombre if area_obj else None

        # Contexto solicitud desde link table
        solicitud_id, _, solicitud_asunto = NotificacionPresenter._get_solicitud_context(notif)

        # Expediente anidado
        expediente_publico = None
        if solicitud_id:
            contexto_list = notif._prefetched_objects_cache.get("contexto_solicitud", []) if hasattr(notif, "_prefetched_objects_cache") else []
            if contexto_list:
                contexto = contexto_list[0]
                solicitud = getattr(contexto, "solicitud", None)
                if solicitud and hasattr(solicitud, "expediente") and solicitud.expediente:
                    expediente_publico = ExpedientePublicoOut(
                        id_publico=solicitud.expediente.id_publico,
                        asunto=solicitud.expediente.asunto,
                    )

        # Período anidado
        periodo_ctx = None
        contexto_list = notif._prefetched_objects_cache.get("contexto_solicitud", []) if hasattr(notif, "_prefetched_objects_cache") else []
        if contexto_list:
            contexto = contexto_list[0]
            periodo = getattr(contexto, "periodo", None)
            if periodo:
                periodo_ctx = PeriodoContextOut(
                    id=periodo.id,
                    numero_ciclo=getattr(periodo, "numero_ciclo", None),
                    esta_abierto=getattr(periodo, "esta_abierto", None),
                )

        # Generada por
        generada_por_nombres = None
        if notif.generada_por:
            generada_por_nombres = (
                f"{notif.generada_por.nombres or ''} "
                f"{notif.generada_por.apellidos or ''}"
            ).strip() or None

        # Estado individual
        estado_individual = NotificacionPresenter._compute_estado_individual(interaccion)

        # Flags de interacción
        vista = interaccion.vista_at is not None if interaccion else False
        abierta = interaccion.abierta_at is not None if interaccion else False
        descartada = interaccion.descartada_at is not None if interaccion else False
        interactuada = vista or abierta or descartada

        # Audiencia
        audiencia_tipo = NotificacionPresenter._compute_audiencia_tipo(notif)

        # Participo
        participo = NotificacionPresenter._compute_participo(notif, usuario_id)

        return NotificacionDetalleOut(
            id=notif.id,
            ambito=notif.ambito,
            evento=notif.evento,
            prioridad=notif.prioridad,
            titulo=notif.titulo,
            mensaje=notif.mensaje,
            ocurrido_en=notif.ocurrido_en,
            interactuada=interactuada,
            vista=vista,
            abierta=abierta,
            descartada=descartada,
            estado_individual=estado_individual,
            audiencia_tipo=audiencia_tipo,
            generada_por_nombres=generada_por_nombres,
            solicitud_id=solicitud_id,
            expediente_publico=expediente_publico,
            area_id=area_id,
            area_nombre=area_nombre,
            periodo=periodo_ctx,
            interacciones=interacciones,
            participo=participo,
            solicitud_asunto=solicitud_asunto,
        )

    @staticmethod
    def present_detail_base(
        notif: Notificacion,
        usuario_id: int,
    ) -> NotificacionDetalleOut:
        """
        Construye un NotificacionDetalleOut para notificaciones sin contexto rico.

        Usa None para expediente_publico y periodo (ej. ámbito SISTEMA sin contexto).

        Args:
            notif: Entidad Notificacion con relaciones eager-loaded
            usuario_id: ID del usuario autenticado

        Returns:
            NotificacionDetalleOut con contexto base (expediente_publico=None, periodo=None)
        """
        # Interacciones del usuario actual
        iu_qs = [
            iu for iu in notif.usuarios_notificados.all()
            if iu.usuario_id == usuario_id
        ]
        interacciones = [
            InteraccionOut(
                usuario_id=iu.usuario_id,
                vista_at=iu.vista_at,
                abierta_at=iu.abierta_at,
                descartada_at=iu.descartada_at,
            )
            for iu in iu_qs
        ]
        interaccion = iu_qs[0] if iu_qs else None

        # Estado individual
        estado_individual = NotificacionPresenter._compute_estado_individual(interaccion)

        # Flags de interacción
        vista = interaccion.vista_at is not None if interaccion else False
        abierta = interaccion.abierta_at is not None if interaccion else False
        descartada = interaccion.descartada_at is not None if interaccion else False
        interactuada = vista or abierta or descartada

        # Generada por
        generada_por_nombres = None
        if notif.generada_por:
            generada_por_nombres = (
                f"{notif.generada_por.nombres or ''} "
                f"{notif.generada_por.apellidos or ''}"
            ).strip() or None

        # Audiencia
        audiencia_tipo = NotificacionPresenter._compute_audiencia_tipo(notif)

        return NotificacionDetalleOut(
            id=notif.id,
            ambito=notif.ambito,
            evento=notif.evento,
            prioridad=notif.prioridad,
            titulo=notif.titulo,
            mensaje=notif.mensaje,
            ocurrido_en=notif.ocurrido_en,
            interactuada=interactuada,
            vista=vista,
            abierta=abierta,
            descartada=descartada,
            estado_individual=estado_individual,
            audiencia_tipo=audiencia_tipo,
            generada_por_nombres=generada_por_nombres,
            solicitud_id=None,
            expediente_publico=None,
            area_id=None,
            area_nombre=None,
            periodo=None,
            interacciones=interacciones,
            participo=None,
            solicitud_asunto=None,
        )
