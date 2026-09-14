"""
UsuarioMencionableSelector — consultas para usuarios mencionables en conversaciones.

Este selector live in infrastructure/ porque depende de modelos de otros módulos
(asignaciones, tramites) y no debe vivir en domain/ para mantener el desacoplamiento.
"""
from dataclasses import dataclass
from uuid import UUID

from django.db.models import Q, QuerySet

from modules.usuarios.domain.models import Usuario, AsignacionUsuario


@dataclass(frozen=True, slots=True)
class UsuarioMencionableCtx:
    """
    Usuario con contexto de participación para respuestas enriquizadas.

    Cuando se consulta por solicitud_id, el selector retorna esta estructura
    en lugar de solo Usuario, para que el controller pueda completar los
    campos area_id, area_nombre, rol, periodo_id, numero_ciclo, tipo_participacion.
    """
    usuario: Usuario
    area_id: UUID | None
    area_nombre: str | None
    rol: str | None
    periodo_id: UUID | None
    numero_ciclo: int | None
    tipo_participacion: str | None


class UsuarioMencionableSelector:
    """
    Selector para usuarios mencionables en el contexto de una solicitud/área.

    Para contexto de solicitud (solicitud_id): consulta a través de
    SolicitudAsignacionUsuario → SolicitudAsignacionPeriodo (abiertos) →
    SolicitudAsignacion → area. Un usuario es mencionable si tiene
    participación activa (fecha_fin IS NULL) en algún período abierto
    de algún área asignada a la solicitud.

    Para contexto explícito de área (area_id sin solicitud_id): usa
    AsignacionUsuario global (comportamiento anterior, sin cambio).

    El método listar_mencionables retorna:
    - Para solicitud_id: list[UsuarioMencionableCtx] con contexto de participación
    - Para area_id: QuerySet[Usuario] (compatible con tests existentes)
    """

    @staticmethod
    def listar_mencionables(
        *,
        solicitud_id: UUID | None = None,
        area_id: UUID | None = None,
        periodo_id: UUID | None = None,
        conversacion_id: UUID | None = None,
        nombre: str | None = None,
    ) -> list[UsuarioMencionableCtx] | QuerySet[Usuario]:
        """
        Lista usuarios mencionables filtrados por contexto.

            Args:
                solicitud_id: UUID de la solicitud (derive áreas asignadas y usa
                    SolicitudAsignacionUsuario para participants activos en
                    períodos abiertos). Retorna list[UsuarioMencionableCtx].
                area_id: UUID del área (filtro explícito, usa AsignacionUsuario).
                    Retorna QuerySet[Usuario] por compatibilidad.
                periodo_id: UUID del período (opcional, narrowing sobre
                    solicitud_id — filtra a participants de un período específico).
                conversacion_id: UUID de la conversación (derive solicitud_id).
                nombre: Texto de búsqueda por nombres, apellidos, username o dni.

        Returns:
            Para solicitud_id: list[UsuarioMencionableCtx] con contexto.
            Para area_id: QuerySet[Usuario] únicos mencionables.
        """
        # ── Derivar solicitud_id desde conversacion_id si es necesario ──
        if conversacion_id is not None and solicitud_id is None:
            from modules.conversaciones.domain.models import SolicitudConversacion

            try:
                bridge = SolicitudConversacion.objects.select_related("solicitud").get(
                    conversacion_id=conversacion_id
                )
                solicitud_id = bridge.solicitud_id
            except SolicitudConversacion.DoesNotExist:
                # No hay bridge, retornar queryset vacío
                return Usuario.objects.none()

        # ── Contexto de solicitud: usar SolicitudAsignacionUsuario ──
        if solicitud_id is not None:
            from modules.asignaciones.domain.models import (
                SolicitudAsignacionPeriodo,
                SolicitudAsignacionUsuario,
            )
            from modules.asignaciones.domain.models import SolicitudAsignacion

            areas_asignadas = set(
                SolicitudAsignacion.objects.filter(solicitud_id=solicitud_id)
                .values_list("area_id", flat=True)
            )

            if not areas_asignadas:
                return []

            qs_participantes = SolicitudAsignacionUsuario.objects.filter(
                periodo__asignacion__solicitud_id=solicitud_id,
                periodo__fecha_fin__isnull=True,  # período abierto
                fecha_fin__isnull=True,  # participación activa
            ).select_related(
                "periodo",
                "periodo__asignacion",
                "periodo__asignacion__area",
                "usuario",
            )

            if periodo_id is not None:
                qs_participantes = qs_participantes.filter(periodo_id=periodo_id)

            # ── Construir resultados enriquecidos ──
            resultados: list[UsuarioMencionableCtx] = []
            usuarios_vistos: set[UUID] = set()

            for partic in qs_participantes:
                uid = partic.usuario_id
                if uid in usuarios_vistos:
                    continue
                usuarios_vistos.add(uid)

                # Filtrar por nombre si se requiere
                if nombre:
                    nombre_lower = nombre.lower().strip()
                    u = partic.usuario
                    if not (
                        (u.nombres and nombre_lower in u.nombres.lower())
                        or (u.apellidos and nombre_lower in u.apellidos.lower())
                        or nombre_lower in u.username.lower()
                        or (u.dni and nombre_lower in u.dni.lower())
                    ):
                        continue

                area = partic.periodo.asignacion.area
                resultados.append(
                    UsuarioMencionableCtx(
                        usuario=partic.usuario,
                        area_id=area.id,
                        area_nombre=area.nombre,
                        rol=partic.rol,
                        periodo_id=partic.periodo_id,
                        numero_ciclo=partic.periodo.numero_ciclo,
                        tipo_participacion=partic.periodo.tipo_participacion,
                    )
                )

            resultados.sort(key=lambda ctx: (ctx.usuario.nombres or "", ctx.usuario.apellidos or ""))
            return resultados

        # ── Contexto de área explícito: usar AsignacionUsuario global ──
        elif area_id is not None:
            qs = AsignacionUsuario.objects.filter(
                area_id=area_id,
                periodo_fin__isnull=True,
            ).select_related("usuario")

            usuario_ids = qs.values_list("usuario_id", flat=True).distinct()
            usuarios_qs = Usuario.objects.filter(id__in=usuario_ids, is_active=True)

            if nombre:
                nombre_lower = nombre.lower().strip()
                usuarios_qs = usuarios_qs.filter(
                    Q(nombres__icontains=nombre_lower)
                    | Q(apellidos__icontains=nombre_lower)
                    | Q(username__icontains=nombre_lower)
                    | Q(dni__icontains=nombre_lower)
                )

            return usuarios_qs.order_by("nombres", "apellidos")

        else:
            # Sin contexto, retornar vacío
            return Usuario.objects.none()
