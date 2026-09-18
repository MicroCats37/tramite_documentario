"""
PeriodoOperacionesFlujo — flujo async para operaciones sobre períodos de asignación.

Transitions:
- Iniciar gestión: PENDIENTE → EN_GESTION
- Tomar período: PENDIENTE → EN_GESTION (con autoasignación del usuario)

El @transaction.atomic() garantiza atomicidad en la transición de estado
y el registro del historial.
"""
from datetime import datetime
from uuid import UUID

from asgiref.sync import sync_to_async
from django.db import models, transaction
from django.utils import timezone
from injector import inject
from ninja.errors import HttpError

from modules.asignaciones.domain.models import (
    SolicitudAsignacionPeriodo,
    SolicitudAsignacionRespuesta,
    SolicitudAsignacionUsuario,
)
from modules.asignaciones.domain.constants import (
    EstadoPeriodo,
    EstadoPeriodoOperativo,
    EstadoRespuesta,
    OrigenEstadoPeriodo,
    TipoCierre,
    TipoParticipacion,
    TipoRespuesta,
)
from modules.asignaciones.domain.services.core.periodo_estado_historial_service import (
    PeriodoEstadoHistorialCoreService,
)
from modules.conversaciones.domain.services.core.mensajeria_service import (
    MensajeriaCoreService,
)


class PeriodoOperacionesFlujo:
    """
    Flujo asíncrono para operaciones sobre períodos de asignación.

    Operaciones:
    - Iniciar gestión: transiciona un período de PENDIENTE a EN_GESTION.
    - Tomar período: transiciona PENDIENTE → EN_GESTION y asigna el usuario como participante.

    El @transaction.atomic() garantiza atomicidad en la transición de estado
    y el registro del historial de estados.
    """

    @inject
    def __init__(
        self,
        periodo_estado_historial_service: PeriodoEstadoHistorialCoreService,
        mensajeria_service: MensajeriaCoreService,
    ):
        self.periodo_estado_historial_service = periodo_estado_historial_service
        self.mensajeria_service = mensajeria_service

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _formatear_mensaje_periodo_sistema(
        operacion: str,
        area_nombre: str,
        numero_ciclo: int,
        actor_nombre: str,
    ) -> str:
        """
        Construye el texto contextual para mensajes de sistema de operaciones de período.

        Args:
            operacion: Nombre de la operación (e.g. "tomó", "inició la gestión",
                       "cerró", "marcó como asignación errónea").
            area_nombre: Nombre del área.
            numero_ciclo: Número de ciclo del período.
            actor_nombre: Nombre completo del usuario que ejecuta la acción.

        Returns:
            Texto del mensaje de sistema.
        """
        return (
            f"El usuario {actor_nombre} {operacion} el período {numero_ciclo} "
            f"del área {area_nombre}."
        )

    @staticmethod
    def _formatear_mensaje_cambio_participacion(
        area_nombre: str,
        numero_ciclo: int,
        nuevo_tipo: str,
        actor_nombre: str,
    ) -> str:
        """
        Construye el texto para el mensaje de cambio de participación.

        Indica el cierre del ciclo anterior y la apertura del nuevo.
        """
        return (
            f"El usuario {actor_nombre} cambió la participación del período "
            f"{numero_ciclo} del área {area_nombre} a {nuevo_tipo}."
        )

    def _crear_mensaje_periodo_sistema_if_present(
        self,
        periodo: SolicitudAsignacionPeriodo,
        ahora: datetime,
        usuario,
        operacion: str,
    ) -> None:
        """
        Crea un mensaje de sistema en la conversación vinculada a la solicitud.

        Si la solicitud no tiene puente de conversación, no hace nada
        (el mensaje es opcional para auditoría).
        """
        try:
            puente = periodo.asignacion.solicitud.conversacionpuente
            conversacion = puente.conversacion
            actor_nombre = (
                f"{usuario.nombres} {usuario.apellidos}".strip() or usuario.username
            )
            contenido = self._formatear_mensaje_periodo_sistema(
                operacion=operacion,
                area_nombre=periodo.asignacion.area.nombre,
                numero_ciclo=periodo.numero_ciclo,
                actor_nombre=actor_nombre,
            )
            self.mensajeria_service.crear_mensaje_sistema(
                conversacion_id=conversacion.id,
                contenido=contenido,
                fecha_envio=ahora,
            )
        except Exception:
            # Silently skip if no conversation bridge exists
            # (audit message is best-effort)
            pass

    def _crear_mensaje_cambio_participacion_if_present(
        self,
        periodo: SolicitudAsignacionPeriodo,
        ahora: datetime,
        usuario,
        nuevo_tipo: str,
    ) -> None:
        """
        Crea un mensaje de sistema para cambio de participación.

        Si la solicitud no tiene puente de conversación, no hace nada.
        """
        try:
            puente = periodo.asignacion.solicitud.conversacionpuente
            conversacion = puente.conversacion
            actor_nombre = (
                f"{usuario.nombres} {usuario.apellidos}".strip() or usuario.username
            )
            contenido = self._formatear_mensaje_cambio_participacion(
                area_nombre=periodo.asignacion.area.nombre,
                numero_ciclo=periodo.numero_ciclo,
                nuevo_tipo=nuevo_tipo,
                actor_nombre=actor_nombre,
            )
            self.mensajeria_service.crear_mensaje_sistema(
                conversacion_id=conversacion.id,
                contenido=contenido,
                fecha_envio=ahora,
            )
        except Exception:
            pass

    async def _proceso_iniciar_gestion(
        self,
        periodo_id: UUID,
        usuario_id: int,
    ):
        """
        Inicia la gestión de un período que se encuentra en PENDIENTE.

        1. Obtiene el período con lock (select_for_update).
        2. Valida que el período existe y está en estado PENDIENTE.
        3. Transiciona el período a EN_GESTION.
        4. Registra el cambio en SolicitudAsignacionPeriodoEstadoHistorial.
        5. Retorna el periodo actualizado con su asignación y solicitud cargadas.

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.
            usuario_id: ID del usuario que inicia la gestión.

        Returns:
            Instancia de SolicitudAsignacionPeriodo con relaciones precargadas.

        Raises:
            HttpError: 404 si el período no existe.
                       409 si el período no está en estado PENDIENTE.
        """
        return await sync_to_async(self._iniciar_gestion_atomica)(
            periodo_id=periodo_id,
            usuario_id=usuario_id,
        )

    @transaction.atomic()
    def _iniciar_gestion_atomica(
        self,
        periodo_id: UUID,
        usuario_id: int,
    ):
        """
        Versión síncrona con @transaction.atomic para iniciar gestión.
        """
        from modules.usuarios.domain.models import Usuario

        ahora = datetime.now()

        # 1. Obtener el período con lock
        try:
            periodo = (
                SolicitudAsignacionPeriodo.objects
                .select_for_update()
                .select_related("asignacion__solicitud")
                .get(id=periodo_id)
            )
        except SolicitudAsignacionPeriodo.DoesNotExist:
            raise HttpError(404, f"Período '{periodo_id}' no encontrado")

        # 2. Validar estado PENDIENTE
        if periodo.estado != EstadoPeriodo.PENDIENTE:
            raise HttpError(
                409,
                f"No se puede iniciar gestión de un período en estado {periodo.estado}",
            )

        # 3. Obtener el usuario
        try:
            usuario = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            raise HttpError(404, f"Usuario '{usuario_id}' no encontrado")

        # 4. Transicionar a EN_GESTION
        periodo.estado = EstadoPeriodo.EN_GESTION
        periodo.save()

        # 5. Registrar historial de estado operativo
        self.periodo_estado_historial_service.registrar_transicion(
            periodo=periodo,
            estado_anterior=EstadoPeriodoOperativo.PENDIENTE,
            estado_nuevo=EstadoPeriodoOperativo.EN_GESTION,
            fecha_cambio=ahora,
            cambiado_por=usuario,
            motivo="Inicio de gestión del período",
            origen=OrigenEstadoPeriodo.AUTOASIGNACION,
        )

        # 6. Crear mensaje de sistema en la conversación
        self._crear_mensaje_periodo_sistema_if_present(
            periodo, ahora, usuario, "inició la gestión",
        )

        # 7. Si la Solicitud está en EN_TRAMITE o REGISTRADA, transicionar a EN_GESTION.
        # setear fecha_inicio_gestion solo si es null (primera vez que inicia gestión).
        from modules.tramites.domain.models import Solicitud
        from modules.tramites.domain.constants import EstadoSolicitud
        from modules.tramites.domain.models.solicitud_historial import OrigenCambio

        solicitud = periodo.asignacion.solicitud
        if solicitud.estado in (EstadoSolicitud.EN_TRAMITE, EstadoSolicitud.REGISTRADA):
            estado_anterior = solicitud.estado
            if solicitud.fecha_inicio_gestion is None:
                solicitud.fecha_inicio_gestion = ahora
            solicitud.estado = EstadoSolicitud.EN_GESTION
            solicitud.save()

            # Historial: EN_TRAMITE/REGISTRADA → EN_GESTION
            from modules.tramites.domain.services.core.solicitud_core_service import (
                SolicitudCoreService,
            )
            solicitud_core = SolicitudCoreService()
            solicitud_core._crear_historial_estado(
                solicitud=solicitud,
                estado_anterior=estado_anterior,
                estado_nuevo=EstadoSolicitud.EN_GESTION,
                cambiado_por_id=usuario.id,
                fecha_cambio=ahora,
                motivo="Inicio de gestión de período",
                origen=OrigenCambio.CAMBIO_ESTADO,
            )

        # 8. Retornar el período con relaciones precargadas
        # Re-fetch con las relaciones necesarias para el presenter
        return (
            SolicitudAsignacionPeriodo.objects
            .select_related(
                "asignacion__solicitud__expediente",
                "asignacion__area",
            )
            .prefetch_related(
                "asignacion__solicitud__asignaciones__area",
                "asignacion__solicitud__asignaciones__periodos",
            )
            .get(id=periodo_id)
        )

    async def _proceso_tomar_periodo(
        self,
        periodo_id: UUID,
        usuario_id: int,
    ):
        """
        El usuario toma el período: se asigna a sí mismo como participante
        y transiciona el período de PENDIENTE a EN_GESTION.

        1. Obtiene el período con lock (select_for_update).
        2. Valida que el período existe y está en estado PENDIENTE.
        3. Crea el registro SolicitudAsignacionUsuario para el usuario (si no existe ya).
        4. Transiciona el período a EN_GESTION.
        5. Registra el cambio en SolicitudAsignacionPeriodoEstadoHistorial.
        6. Retorna el período actualizado con su asignación y solicitud cargadas.

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.
            usuario_id: ID del usuario que toma el período.

        Returns:
            Instancia de SolicitudAsignacionPeriodo con relaciones precargadas.

        Raises:
            HttpError: 404 si el período no existe.
                       404 si el usuario no existe.
                       409 si el período no está en estado PENDIENTE.
                       409 si el usuario ya está asignado activamente al período.
        """
        return await sync_to_async(self._tomar_periodo_atomica)(
            periodo_id=periodo_id,
            usuario_id=usuario_id,
        )

    @transaction.atomic()
    def _tomar_periodo_atomica(
        self,
        periodo_id: UUID,
        usuario_id: int,
    ):
        """
        Versión síncrona con @transaction.atomic para tomar un período.
        """
        from modules.usuarios.domain.models import Usuario

        ahora = datetime.now()

        # 1. Obtener el período con lock
        try:
            periodo = (
                SolicitudAsignacionPeriodo.objects
                .select_for_update()
                .select_related("asignacion__solicitud")
                .get(id=periodo_id)
            )
        except SolicitudAsignacionPeriodo.DoesNotExist:
            raise HttpError(404, f"Período '{periodo_id}' no encontrado")

        # 2. Validar estado PENDIENTE
        if periodo.estado != EstadoPeriodo.PENDIENTE:
            raise HttpError(
                409,
                f"No se puede tomar un período en estado {periodo.estado}",
            )

        # 3. Obtener el usuario
        try:
            usuario = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            raise HttpError(404, f"Usuario '{usuario_id}' no encontrado")

        # 4. Verificar que el usuario no esté ya activamente asignado a este período
        ya_asignado = SolicitudAsignacionUsuario.objects.filter(
            periodo=periodo,
            usuario=usuario,
            fecha_fin__isnull=True,
        ).exists()
        if ya_asignado:
            raise HttpError(
                409,
                f"El usuario ya está asignado activamente a este período",
            )

        # 5. Crear el registro de asignación del usuario al período
        SolicitudAsignacionUsuario.objects.create(
            periodo=periodo,
            usuario=usuario,
            rol="Responsable",
            fecha_inicio=ahora,
            asignado_por=usuario,
        )

        # 6. Transicionar a EN_GESTION
        periodo.estado = EstadoPeriodo.EN_GESTION
        periodo.save()

        # 7. Registrar historial de estado operativo
        self.periodo_estado_historial_service.registrar_transicion(
            periodo=periodo,
            estado_anterior=EstadoPeriodoOperativo.PENDIENTE,
            estado_nuevo=EstadoPeriodoOperativo.EN_GESTION,
            fecha_cambio=ahora,
            cambiado_por=usuario,
            motivo="Usuario toma el período",
            origen=OrigenEstadoPeriodo.AUTOASIGNACION,
        )

        # 8. Crear mensaje de sistema en la conversación
        self._crear_mensaje_periodo_sistema_if_present(
            periodo, ahora, usuario, "tomó",
        )

        # 9. Si la Solicitud está en EN_TRAMITE o REGISTRADA, transicionar a EN_GESTION.
        # setear fecha_inicio_gestion solo si es null (primera vez que inicia gestión).
        from modules.tramites.domain.models import Solicitud
        from modules.tramites.domain.constants import EstadoSolicitud
        from modules.tramites.domain.models.solicitud_historial import OrigenCambio

        solicitud = periodo.asignacion.solicitud
        if solicitud.estado in (EstadoSolicitud.EN_TRAMITE, EstadoSolicitud.REGISTRADA):
            estado_anterior = solicitud.estado
            if solicitud.fecha_inicio_gestion is None:
                solicitud.fecha_inicio_gestion = ahora
            solicitud.estado = EstadoSolicitud.EN_GESTION
            solicitud.save()

            # Historial: EN_TRAMITE/REGISTRADA → EN_GESTION
            from modules.tramites.domain.services.core.solicitud_core_service import (
                SolicitudCoreService,
            )
            solicitud_core = SolicitudCoreService()
            solicitud_core._crear_historial_estado(
                solicitud=solicitud,
                estado_anterior=estado_anterior,
                estado_nuevo=EstadoSolicitud.EN_GESTION,
                cambiado_por_id=usuario.id,
                fecha_cambio=ahora,
                motivo="Usuario toma el período",
                origen=OrigenCambio.CAMBIO_ESTADO,
            )

        # 10. Retornar el período con relaciones precargadas
        return (
            SolicitudAsignacionPeriodo.objects
            .select_related(
                "asignacion__solicitud__expediente",
                "asignacion__area",
            )
            .prefetch_related(
                "asignacion__solicitud__asignaciones__area",
                "asignacion__solicitud__asignaciones__periodos",
                "usuarios__usuario",
            )
            .get(id=periodo_id)
        )

    async def _proceso_agregar_usuario(
        self,
        periodo_id: UUID,
        usuario_id: UUID,
        usuario_a_asignar_id: UUID,
        rol: str | None = None,
    ):
        """
        Asigna un usuario como participante a un período existente.

        A diferencia de _proceso_tomar_periodo (donde el usuario se autoasigna),
        aquí el usuario autenticado (usuario_id) asigna a otro usuario (usuario_a_asignar_id)
        como participante del período.

        No cambia el estado del período — solo agrega un SolicitudAsignacionUsuario.

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.
            usuario_id: UUID del usuario que realiza la asignación.
            usuario_a_asignar_id: UUID del usuario a asignar como participante.
            rol: Rol del participante (default "Responsable").

        Returns:
            Instancia de SolicitudAsignacionPeriodo con relaciones precargadas.

        Raises:
            HttpError: 404 si el período no existe.
                       404 si el usuario a asignar no existe.
                       409 si el período está CERRADO.
                       409 si el usuario ya está activamente asignado al período.
        """
        return await sync_to_async(self._agregar_usuario_atomica)(
            periodo_id=periodo_id,
            usuario_id=usuario_id,
            usuario_a_asignar_id=usuario_a_asignar_id,
            rol=rol,
        )

    @transaction.atomic()
    def _agregar_usuario_atomica(
        self,
        periodo_id: UUID,
        usuario_id: UUID,
        usuario_a_asignar_id: UUID,
        rol: str | None = None,
    ):
        """
        Versión síncrona con @transaction.atomic para agregar un usuario a un período.
        """
        from modules.usuarios.domain.models import Usuario

        ahora = datetime.now()
        rol_efectivo = rol or "Responsable"

        # 1. Obtener el período con lock
        try:
            periodo = (
                SolicitudAsignacionPeriodo.objects
                .select_for_update()
                .select_related("asignacion__solicitud")
                .get(id=periodo_id)
            )
        except SolicitudAsignacionPeriodo.DoesNotExist:
            raise HttpError(404, f"Período '{periodo_id}' no encontrado")

        # 2. Validar que el período no esté CERRADO
        if periodo.estado == EstadoPeriodo.CERRADO:
            raise HttpError(
                409,
                f"No se puede agregar un usuario a un período en estado {periodo.estado}",
            )

        # 3. Obtener el usuario que realiza la asignación
        try:
            usuario = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            raise HttpError(404, f"Usuario '{usuario_id}' no encontrado")

        # 4. Obtener el usuario a asignar
        try:
            usuario_a_asignar = Usuario.objects.get(id=usuario_a_asignar_id)
        except Usuario.DoesNotExist:
            raise HttpError(404, f"Usuario '{usuario_a_asignar_id}' no encontrado")

        # 5. Verificar que el usuario a asignar no esté ya activamente asignado
        ya_asignado = SolicitudAsignacionUsuario.objects.filter(
            periodo=periodo,
            usuario=usuario_a_asignar,
            fecha_fin__isnull=True,
        ).exists()
        if ya_asignado:
            raise HttpError(
                409,
                f"El usuario '{usuario_a_asignar.username}' ya está asignado activamente a este período",
            )

        # 6. Crear el registro de asignación del usuario al período
        SolicitudAsignacionUsuario.objects.create(
            periodo=periodo,
            usuario=usuario_a_asignar,
            rol=rol_efectivo,
            fecha_inicio=ahora,
            asignado_por=usuario,
        )

        # 7. Retornar el período con relaciones precargadas
        return (
            SolicitudAsignacionPeriodo.objects
            .select_related(
                "asignacion__solicitud__expediente",
                "asignacion__area",
            )
            .prefetch_related(
                "asignacion__solicitud__asignaciones__area",
                "asignacion__solicitud__asignaciones__periodos",
                "usuarios__usuario",
            )
            .get(id=periodo_id)
        )

    async def _proceso_finalizar(
        self,
        periodo_id: UUID,
        usuario_id: int,
        tipo_cierre: str | None = None,
        motivo_cierre: str | None = None,
        observacion: str | None = None,
    ):
        """
        Finaliza un período de asignación, transicionándolo a CERRADO.

        1. Obtiene el período con lock (select_for_update).
        2. Valida que el período existe y no está ya CERRADO.
        3. Transiciona el período a CERRADO (fecha_fin, finalizado_por, tipo_cierre).
        4. Registra el cambio en SolicitudAsignacionPeriodoEstadoHistorial.
        5. Retorna el período actualizado con su asignación y solicitud cargadas.

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.
            usuario_id: ID del usuario que finaliza el período.
            tipo_cierre: Tipo de cierre (default FINALIZADO).
            motivo_cierre: Motivo opcional del cierre.
            observacion: Observación opcional.

        Returns:
            Instancia de SolicitudAsignacionPeriodo con relaciones precargadas.

        Raises:
            HttpError: 404 si el período no existe.
                       409 si el período ya está CERRADO.
        """
        return await sync_to_async(self._finalizar_atomica)(
            periodo_id=periodo_id,
            usuario_id=usuario_id,
            tipo_cierre=tipo_cierre,
            motivo_cierre=motivo_cierre,
            observacion=observacion,
        )

    @transaction.atomic()
    def _finalizar_atomica(
        self,
        periodo_id: UUID,
        usuario_id: int,
        tipo_cierre: str | None = None,
        motivo_cierre: str | None = None,
        observacion: str | None = None,
    ):
        """
        Versión síncrona con @transaction.atomic para finalizar un período.
        """
        from modules.usuarios.domain.models import Usuario

        ahora = datetime.now()
        tipo_cierre_efectivo = tipo_cierre or TipoCierre.FINALIZADO

        # 1. Obtener el período con lock
        try:
            periodo = (
                SolicitudAsignacionPeriodo.objects
                .select_for_update()
                .select_related("asignacion__solicitud")
                .get(id=periodo_id)
            )
        except SolicitudAsignacionPeriodo.DoesNotExist:
            raise HttpError(404, f"Período '{periodo_id}' no encontrado")

        # 2. Validar que el período no esté ya CERRADO
        if periodo.estado == EstadoPeriodo.CERRADO:
            raise HttpError(
                409,
                f"No se puede finalizar un período en estado {periodo.estado}",
            )

        # 3. Obtener el usuario
        try:
            usuario = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            raise HttpError(404, f"Usuario '{usuario_id}' no encontrado")

        estado_anterior = periodo.estado

        # 4. Transicionar a CERRADO
        periodo.estado = EstadoPeriodo.CERRADO
        periodo.fecha_fin = ahora
        periodo.finalizado_por = usuario
        periodo.tipo_cierre = tipo_cierre_efectivo
        if motivo_cierre:
            periodo.motivo_cierre = motivo_cierre
        if observacion:
            periodo.observacion = observacion
        periodo.save()

        # 5. Registrar historial de estado operativo
        self.periodo_estado_historial_service.registrar_transicion(
            periodo=periodo,
            estado_anterior=EstadoPeriodoOperativo.EN_GESTION
            if estado_anterior == EstadoPeriodo.EN_GESTION
            else EstadoPeriodoOperativo.PENDIENTE,
            estado_nuevo=EstadoPeriodoOperativo.CERRADO,
            fecha_cambio=ahora,
            cambiado_por=usuario,
            motivo=motivo_cierre or "Cierre del período",
            origen=OrigenEstadoPeriodo.CIERRE,
        )

        # 6. Crear mensaje de sistema en la conversación
        self._crear_mensaje_periodo_sistema_if_present(
            periodo, ahora, usuario, "cerró",
        )

        # 7. Retornar el período con relaciones precargadas
        return (
            SolicitudAsignacionPeriodo.objects
            .select_related(
                "asignacion__solicitud__expediente",
                "asignacion__area",
            )
            .prefetch_related(
                "asignacion__solicitud__asignaciones__area",
                "asignacion__solicitud__asignaciones__periodos",
                "usuarios__usuario",
            )
            .get(id=periodo_id)
        )

    async def _proceso_marcar_erronea(
        self,
        periodo_id: UUID,
        usuario_id: int,
        motivo_cierre: str | None = None,
        observacion: str | None = None,
    ):
        """
        Marca un período como asignación errónea, transicionándolo a CERRADO
        con tipo_cierre=ASIGNACION_ERRONEA.

        1. Obtiene el período con lock (select_for_update).
        2. Valida que el período existe y no está ya CERRADO.
        3. Transiciona el período a CERRADO con tipo_cierre=ASIGNACION_ERRONEA.
        4. Registra el cambio en SolicitudAsignacionPeriodoEstadoHistorial.
        5. Retorna el período actualizado con su asignación y solicitud cargadas.

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.
            usuario_id: ID del usuario que marca la asignación como errónea.
            motivo_cierre: Motivo opcional del cierre.
            observacion: Observación opcional.

        Returns:
            Instancia de SolicitudAsignacionPeriodo con relaciones precargadas.

        Raises:
            HttpError: 404 si el período no existe.
                       409 si el período ya está CERRADO.
        """
        return await sync_to_async(self._marcar_erronea_atomica)(
            periodo_id=periodo_id,
            usuario_id=usuario_id,
            motivo_cierre=motivo_cierre,
            observacion=observacion,
        )

    @transaction.atomic()
    def _marcar_erronea_atomica(
        self,
        periodo_id: UUID,
        usuario_id: int,
        motivo_cierre: str | None = None,
        observacion: str | None = None,
    ):
        """
        Versión síncrona con @transaction.atomic para marcar asignación errónea.
        """
        from modules.usuarios.domain.models import Usuario

        ahora = datetime.now()

        # 1. Obtener el período con lock
        try:
            periodo = (
                SolicitudAsignacionPeriodo.objects
                .select_for_update()
                .select_related("asignacion__solicitud")
                .get(id=periodo_id)
            )
        except SolicitudAsignacionPeriodo.DoesNotExist:
            raise HttpError(404, f"Período '{periodo_id}' no encontrado")

        # 2. Validar que el período no esté ya CERRADO
        if periodo.estado == EstadoPeriodo.CERRADO:
            raise HttpError(
                409,
                f"No se puede marcar como errónea un período en estado {periodo.estado}",
            )

        # 3. Obtener el usuario
        try:
            usuario = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            raise HttpError(404, f"Usuario '{usuario_id}' no encontrado")

        estado_anterior = periodo.estado

        # 4. Transicionar a CERRADO con tipo ASIGNACION_ERRONEA
        periodo.estado = EstadoPeriodo.CERRADO
        periodo.fecha_fin = ahora
        periodo.finalizado_por = usuario
        periodo.tipo_cierre = TipoCierre.ASIGNACION_ERRONEA
        if motivo_cierre:
            periodo.motivo_cierre = motivo_cierre
        if observacion:
            periodo.observacion = observacion
        periodo.save()

        # 5. Registrar historial de estado operativo
        self.periodo_estado_historial_service.registrar_transicion(
            periodo=periodo,
            estado_anterior=EstadoPeriodoOperativo.EN_GESTION
            if estado_anterior == EstadoPeriodo.EN_GESTION
            else EstadoPeriodoOperativo.PENDIENTE,
            estado_nuevo=EstadoPeriodoOperativo.CERRADO,
            fecha_cambio=ahora,
            cambiado_por=usuario,
            motivo=motivo_cierre or "Asignación errónea",
            origen=OrigenEstadoPeriodo.ASIGNACION_ERRONEA,
        )

        # 6. Crear mensaje de sistema en la conversación
        self._crear_mensaje_periodo_sistema_if_present(
            periodo, ahora, usuario, "marcó como asignación errónea",
        )

        # 7. Retornar el período con relaciones precargadas
        return (
            SolicitudAsignacionPeriodo.objects
            .select_related(
                "asignacion__solicitud__expediente",
                "asignacion__area",
            )
            .prefetch_related(
                "asignacion__solicitud__asignaciones__area",
                "asignacion__solicitud__asignaciones__periodos",
                "usuarios__usuario",
            )
            .get(id=periodo_id)
        )

    async def _proceso_cambiar_participacion(
        self,
        periodo_id: UUID,
        usuario_id: int,
        nuevo_tipo: str,
        motivo: str | None = None,
    ):
        """
        Cambia el tipo de participación de un período (PRINCIPAL ↔ ADJUNTA).

        Cierra el período actual con tipo_cierre=CAMBIO_PARTICIPACION y crea
        un nuevo período PENDIENTE con el nuevo tipo de participación.

        1. Obtiene el período con lock (select_for_update).
        2. Valida que el período existe.
        3. Valida que el nuevo tipo es PRINCIPAL o ADJUNTA.
        4. Valida que el período no esté CERRADO.
        5. Valida que el nuevo tipo sea diferente al actual (no es un no-op).
        6. Cierra el período actual (estado=CERRADO, tipo_cierre=CAMBIO_PARTICIPACION).
        7. Crea un nuevo período PENDIENTE con el nuevo tipo de participación.
        8. Registra dos histiales: cierre del anterior y creación del nuevo.
        9. Retorna la solicitud con los períodos actualizados.

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.
            usuario_id: ID del usuario que ejecuta el cambio.
            nuevo_tipo: Nuevo tipo de participación (PRINCIPAL o ADJUNTA).
            motivo: Motivo opcional del cambio de participación.

        Returns:
            Instancia de SolicitudAsignacionPeriodo (nuevo período) con relaciones precargadas.

        Raises:
            HttpError: 404 si el período no existe.
                       400 si el tipo de participación no es PRINCIPAL ni ADJUNTA.
                       409 si el período está CERRADO.
                       409 si el tipo nuevo es igual al actual.
        """
        return await sync_to_async(self._cambiar_participacion_atomica)(
            periodo_id=periodo_id,
            usuario_id=usuario_id,
            nuevo_tipo=nuevo_tipo,
            motivo=motivo,
        )

    @transaction.atomic()
    def _cambiar_participacion_atomica(
        self,
        periodo_id: UUID,
        usuario_id: int,
        nuevo_tipo: str,
        motivo: str | None = None,
    ):
        """
        Versión síncrona con @transaction.atomic para cambiar participación.
        Cierra el período actual y crea uno nuevo con el tipo de participación solicitado.
        """
        from modules.usuarios.domain.models import Usuario

        ahora = datetime.now()

        # Validar tipo nuevo
        if nuevo_tipo not in (TipoParticipacion.PRINCIPAL, TipoParticipacion.ADJUNTA):
            raise HttpError(
                400,
                f"Tipo de participación '{nuevo_tipo}' no válido. Use PRINCIPAL o ADJUNTA.",
            )

        # 1. Obtener el período con lock
        try:
            periodo = (
                SolicitudAsignacionPeriodo.objects
                .select_for_update()
                .select_related("asignacion__solicitud")
                .get(id=periodo_id)
            )
        except SolicitudAsignacionPeriodo.DoesNotExist:
            raise HttpError(404, f"Período '{periodo_id}' no encontrado")

        # 2. Validar que el período no esté CERRADO
        if periodo.estado == EstadoPeriodo.CERRADO:
            raise HttpError(
                409,
                f"No se puede cambiar la participación de un período en estado {periodo.estado}",
            )

        # 3. Validar que el nuevo tipo sea diferente al actual
        if periodo.tipo_participacion == nuevo_tipo:
            raise HttpError(
                409,
                f"El período ya tiene tipo de participación '{nuevo_tipo}'",
            )

        # 4. Obtener el usuario
        try:
            usuario = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            raise HttpError(404, f"Usuario '{usuario_id}' no encontrado")

        tipo_anterior = periodo.tipo_participacion
        estado_anterior_operativo = (
            EstadoPeriodoOperativo.EN_GESTION
            if periodo.estado == EstadoPeriodo.EN_GESTION
            else EstadoPeriodoOperativo.PENDIENTE
        )
        motivo_display = motivo or f"Cambio de participación: {tipo_anterior} → {nuevo_tipo}"

        # 5. Cerrar el período actual
        periodo.estado = EstadoPeriodo.CERRADO
        periodo.fecha_fin = ahora
        periodo.finalizado_por = usuario
        periodo.tipo_cierre = TipoCierre.CAMBIO_PARTICIPACION
        if motivo:
            periodo.motivo_cierre = motivo
        periodo.save()

        # 6. Registrar historial de cierre del período anterior
        self.periodo_estado_historial_service.registrar_transicion(
            periodo=periodo,
            estado_anterior=estado_anterior_operativo,
            estado_nuevo=EstadoPeriodoOperativo.CERRADO,
            fecha_cambio=ahora,
            cambiado_por=usuario,
            motivo=motivo_display,
            origen=OrigenEstadoPeriodo.CAMBIO_PARTICIPACION,
        )

        # 7. Calcular el siguiente numero_ciclo
        max_ciclo = (
            SolicitudAsignacionPeriodo.objects
            .filter(asignacion=periodo.asignacion)
            .aggregate(models.Max("numero_ciclo"))["numero_ciclo__max"]
            or 0
        )
        nuevo_numero_ciclo = max_ciclo + 1

        # 8. Crear el nuevo período PENDIENTE
        nuevo_periodo = SolicitudAsignacionPeriodo.objects.create(
            asignacion=periodo.asignacion,
            numero_ciclo=nuevo_numero_ciclo,
            tipo_participacion=nuevo_tipo,
            estado=EstadoPeriodo.PENDIENTE,
            fecha_inicio=ahora,
            iniciado_por=usuario,
        )

        # 9. Registrar historial de creación del nuevo período
        self.periodo_estado_historial_service.registrar_transicion(
            periodo=nuevo_periodo,
            estado_anterior=None,
            estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
            fecha_cambio=ahora,
            cambiado_por=usuario,
            motivo=motivo_display,
            origen=OrigenEstadoPeriodo.CAMBIO_PARTICIPACION,
        )

        # 10. Crear mensaje de sistema para cambio de participación
        self._crear_mensaje_cambio_participacion_if_present(
            periodo, ahora, usuario, nuevo_tipo,
        )

        # 11. Retornar el nuevo período con relaciones precargadas
        return (
            SolicitudAsignacionPeriodo.objects
            .select_related(
                "asignacion__solicitud__expediente",
                "asignacion__area",
            )
            .prefetch_related(
                "asignacion__solicitud__asignaciones__area",
                "asignacion__solicitud__asignaciones__periodos",
                "usuarios__usuario",
            )
            .get(id=nuevo_periodo.id)
        )

    async def _proceso_crear_respuesta_borrador(
        self,
        periodo_id: UUID,
        usuario_id: int,
        tipo_respuesta: str,
        contenido: str | None = None,
        archivo: str | None = None,
        observacion: str | None = None,
    ):
        """
        Crea una respuesta en estado BORRADOR para un período.

        El borrador puede crearse en cualquier momento mientras el período esté
        abierto (PENDIENTE o EN_GESTION). No requiere que el usuario sea el único
        participante activo.

        Validaciones:
        1. El período existe (404 si no).
        2. El período no está CERRADO (409 si ya cerrado).
        3. El tipo_respuesta es válido (400 si no).

        Efecto:
        - Crea SolicitudAsignacionRespuesta con estado=BORRADOR.
        - emitido_por y fecha_emision quedan NULL (se setearán al emitir).
        - version=1.

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.
            usuario_id: ID del usuario que crea la respuesta.
            tipo_respuesta: Tipo de respuesta (INFORME, OBSERVACION, etc.).
            contenido: Contenido o texto de la respuesta (opcional).
            archivo: Ruta del archivo adjunto (opcional).
            observacion: Observación adicional (opcional).

        Returns:
            Instancia de SolicitudAsignacionRespuesta en estado BORRADOR.

        Raises:
            HttpError: 404 si el período no existe.
                       409 si el período está CERRADO.
                       400 si el tipo de respuesta no es válido.
        """
        return await sync_to_async(self._crear_respuesta_borrador_atomica)(
            periodo_id=periodo_id,
            usuario_id=usuario_id,
            tipo_respuesta=tipo_respuesta,
            contenido=contenido,
            archivo=archivo,
            observacion=observacion,
        )

    @transaction.atomic()
    def _crear_respuesta_borrador_atomica(
        self,
        periodo_id: UUID,
        usuario_id: int,
        tipo_respuesta: str,
        contenido: str | None = None,
        archivo: str | None = None,
        observacion: str | None = None,
    ):
        """
        Versión síncrona con @transaction.atomic para crear respuesta borrador.
        """
        # Validar tipo_respuesta
        if tipo_respuesta not in (TipoRespuesta.INFORME, TipoRespuesta.OBSERVACION,
                                   TipoRespuesta.CONFORMIDAD, TipoRespuesta.DESCARGO,
                                   TipoRespuesta.OTRO):
            raise HttpError(
                400,
                f"Tipo de respuesta '{tipo_respuesta}' no válido. "
                f"Use: INFORME, OBSERVACION, CONFORMIDAD, DESCARGO u OTRO.",
            )

        # 1. Obtener el período con lock
        try:
            periodo = (
                SolicitudAsignacionPeriodo.objects
                .select_related("asignacion__solicitud")
                .get(id=periodo_id)
            )
        except SolicitudAsignacionPeriodo.DoesNotExist:
            raise HttpError(404, f"Período '{periodo_id}' no encontrado")

        # 2. Validar que el período no esté CERRADO
        if periodo.estado == EstadoPeriodo.CERRADO:
            raise HttpError(
                409,
                f"No se puede crear una respuesta para un período en estado {periodo.estado}",
            )

        # 3. Crear la respuesta en estado BORRADOR
        respuesta = SolicitudAsignacionRespuesta.objects.create(
            periodo=periodo,
            tipo_respuesta=tipo_respuesta,
            contenido=contenido,
            archivo=archivo,
            estado=EstadoRespuesta.BORRADOR,
            version=1,
            observacion=observacion,
            # emitido_por y fecha_emision quedan NULL para BORRADOR
        )

        # 4. Retornar la respuesta con relaciones precargadas
        return (
            SolicitudAsignacionRespuesta.objects
            .select_related("periodo", "emitido_por")
            .get(id=respuesta.id)
        )

    # ── 5.3: Emitir respuesta ────────────────────────────────────────────────

    async def _proceso_emitir_respuesta(
        self,
        respuesta_id: UUID,
        usuario_id: int,
    ):
        """
        Emite una respuesta que se encuentra en estado BORRADOR.

        La emisión es irreversible: transiciona la respuesta de BORRADOR a EMITIDA,
        registrando la fecha de emisión y el usuario que la emitió.

        Validaciones:
        1. La respuesta existe (404 si no).
        2. La respuesta está en estado BORRADOR (400 si no).
        3. El período asociado no está CERRADO (409 si cerrado).

        Efecto:
        - estado → EMITIDA
        - fecha_emision → now()
        - emitido_por → usuario autenticado

        Args:
            respuesta_id: UUID de la SolicitudAsignacionRespuesta.
            usuario_id: ID del usuario que emite la respuesta.

        Returns:
            Instancia de SolicitudAsignacionRespuesta en estado EMITIDA.

        Raises:
            HttpError: 404 si la respuesta no existe.
                       400 si la respuesta no está en estado BORRADOR.
                       409 si el período está CERRADO.
        """
        return await sync_to_async(self._emitir_respuesta_atomica)(
            respuesta_id=respuesta_id,
            usuario_id=usuario_id,
        )

    @transaction.atomic()
    def _emitir_respuesta_atomica(
        self,
        respuesta_id: UUID,
        usuario_id: int,
    ):
        """
        Versión síncrona con @transaction.atomic para emitir respuesta.
        """
        from modules.usuarios.domain.models import Usuario

        # 1. Obtener la respuesta con lock
        try:
            respuesta = (
                SolicitudAsignacionRespuesta.objects
                .select_related("periodo")
                .get(id=respuesta_id)
            )
        except SolicitudAsignacionRespuesta.DoesNotExist:
            raise HttpError(404, f"Respuesta '{respuesta_id}' no encontrada")

        # 2. Validar que la respuesta está en estado BORRADOR
        if respuesta.estado != EstadoRespuesta.BORRADOR:
            raise HttpError(
                400,
                f"La respuesta no puede ser emitida. "
                f"Estado actual: {respuesta.estado}. Solo se pueden emitir respuestas en BORRADOR.",
            )

        # 3. Validar que el período no esté CERRADO
        if respuesta.periodo.estado == EstadoPeriodo.CERRADO:
            raise HttpError(
                409,
                f"No se puede emitir una respuesta de un período en estado CERRADO.",
            )

        # 4. Obtener el usuario que emite
        try:
            usuario = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            raise HttpError(404, f"Usuario '{usuario_id}' no encontrado")

        # 5. Emitir la respuesta
        respuesta.estado = EstadoRespuesta.EMITIDA
        respuesta.fecha_emision = timezone.now()
        respuesta.emitido_por = usuario
        respuesta.save(update_fields=["estado", "fecha_emision", "emitido_por", "updated_at"])

        # 6. Retornar la respuesta con relaciones precargadas
        return (
            SolicitudAsignacionRespuesta.objects
            .select_related("periodo", "emitido_por")
            .get(id=respuesta.id)
        )

    # ── 5.4: Anular respuesta ────────────────────────────────────────────────

    async def _proceso_anular_respuesta(
        self,
        respuesta_id: UUID,
        usuario_id: int,
    ):
        """
        Anula una respuesta que se encuentra en estado EMITIDA.

        La anulación es irreversible: transiciona la respuesta de EMITIDA a ANULADA.

        Validaciones:
        1. La respuesta existe (404 si no).
        2. La respuesta está en estado EMITIDA (400 si no).

        Efecto:
        - estado → ANULADA

        Args:
            respuesta_id: UUID de la SolicitudAsignacionRespuesta.
            usuario_id: ID del usuario que anula la respuesta.

        Returns:
            Instancia de SolicitudAsignacionRespuesta en estado ANULADA.

        Raises:
            HttpError: 404 si la respuesta no existe.
                       400 si la respuesta no está en estado EMITIDA.
        """
        return await sync_to_async(self._anular_respuesta_atomica)(
            respuesta_id=respuesta_id,
            usuario_id=usuario_id,
        )

    @transaction.atomic()
    def _anular_respuesta_atomica(
        self,
        respuesta_id: UUID,
        usuario_id: int,
    ):
        """
        Versión síncrona con @transaction.atomic para anular respuesta.
        """
        # 1. Obtener la respuesta con lock
        try:
            respuesta = (
                SolicitudAsignacionRespuesta.objects
                .select_related("periodo")
                .get(id=respuesta_id)
            )
        except SolicitudAsignacionRespuesta.DoesNotExist:
            raise HttpError(404, f"Respuesta '{respuesta_id}' no encontrada")

        # 2. Validar que la respuesta está en estado EMITIDA
        if respuesta.estado != EstadoRespuesta.EMITIDA:
            raise HttpError(
                400,
                f"La respuesta no puede ser anulada. "
                f"Estado actual: {respuesta.estado}. Solo se pueden anular respuestas en estado EMITIDA.",
            )

        # 3. Anular la respuesta
        respuesta.estado = EstadoRespuesta.ANULADA
        respuesta.save(update_fields=["estado", "updated_at"])

        # 4. Retornar la respuesta con relaciones precargadas
        return (
            SolicitudAsignacionRespuesta.objects
            .select_related("periodo", "emitido_por")
            .get(id=respuesta.id)
        )

    # ── 5.5: Rectificar respuesta ─────────────────────────────────────────────

    async def _proceso_rectificar_respuesta(
        self,
        respuesta_id: UUID,
        usuario_id: int,
    ):
        """
        Rectifica una respuesta que se encuentra en estado EMITIDA.

        La rectificación es una corrección formal de una respuesta ya emitida:
        transiciona la respuesta de EMITIDA a RECTIFICADA.

        Validaciones:
        1. La respuesta existe (404 si no).
        2. La respuesta está en estado EMITIDA (400 si no).

        Efecto:
        - estado → RECTIFICADA

        Args:
            respuesta_id: UUID de la SolicitudAsignacionRespuesta.
            usuario_id: ID del usuario que rectifica la respuesta.

        Returns:
            Instancia de SolicitudAsignacionRespuesta en estado RECTIFICADA.

        Raises:
            HttpError: 404 si la respuesta no existe.
                       400 si la respuesta no está en estado EMITIDA.
        """
        return await sync_to_async(self._rectificar_respuesta_atomica)(
            respuesta_id=respuesta_id,
            usuario_id=usuario_id,
        )

    @transaction.atomic()
    def _rectificar_respuesta_atomica(
        self,
        respuesta_id: UUID,
        usuario_id: int,
    ):
        """
        Versión síncrona con @transaction.atomic para rectificar respuesta.
        """
        # 1. Obtener la respuesta con lock
        try:
            respuesta = (
                SolicitudAsignacionRespuesta.objects
                .select_related("periodo")
                .get(id=respuesta_id)
            )
        except SolicitudAsignacionRespuesta.DoesNotExist:
            raise HttpError(404, f"Respuesta '{respuesta_id}' no encontrada")

        # 2. Validar que la respuesta está en estado EMITIDA
        if respuesta.estado != EstadoRespuesta.EMITIDA:
            raise HttpError(
                400,
                f"La respuesta no puede ser rectificada. "
                f"Estado actual: {respuesta.estado}. Solo se pueden rectificar respuestas en estado EMITIDA.",
            )

        # 3. Rectificar la respuesta
        respuesta.estado = EstadoRespuesta.RECTIFICADA
        respuesta.save(update_fields=["estado", "updated_at"])

        # 4. Retornar la respuesta con relaciones precargadas
        return (
            SolicitudAsignacionRespuesta.objects
            .select_related("periodo", "emitido_por")
            .get(id=respuesta.id)
        )
