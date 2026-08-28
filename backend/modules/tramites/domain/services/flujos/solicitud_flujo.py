"""
SolicitudCreacionFlujo — flujo async para creación atómica de Solicitud con distribución.

transaction.atomic() vive AQUÍ — en el flujo que coordina la creación
compuesta de solicitud + historial + asignaciones + notificaciones.
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
from datetime import datetime

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.db import transaction
from injector import inject
from ninja.errors import HttpError

from modules.tramites.domain.models import Solicitud, Expediente, ExpedienteAntecedente
from modules.tramites.domain.constants import EstadoSolicitud
from modules.tramites.domain.models.solicitud_historial import OrigenCambio
from modules.tramites.presentation.schemas.solicitud_in import (
    SolicitudCreateIn,
    SolicitudHibridaCreateIn,
)
from modules.tramites.domain.services.flujos.expediente_flujo import ExpedienteCreacionFlujo
from modules.tramites.domain.services.core.solicitud_core_service import (
    SolicitudCoreService,
)
from modules.asignaciones.domain.services.core.asignacion_core_service import (
    AsignacionCoreService,
)
from modules.asignaciones.domain.models.notificacion import Notificacion
from modules.asignaciones.domain.constants import (
    TipoNotificacion,
    EstadoNotificacion,
    EstadoPeriodo,
)
from modules.usuarios.domain.models import Area


class SolicitudCreacionFlujo:
    """
    Flujo asíncrono para creación de Solicitud con distribución de áreas.

    Coordina la creación atómica de:
    1. Solicitud (cabecera del trámite, estado REGISTRADA o EN_GESTION)
    2. SolicitudEstadoHistorial (registro de auditoría)
    3. SolicitudAsignacion por cada área del payload
    4. SolicitudAsignacionPeriodo (ciclo=1)
    5. Notificacion para cada área

    El @transaction.atomic() garantiza que si falla cualquier operación,
    se revierte todo.
    """

    @inject
    def __init__(
        self,
        solicitud_core: SolicitudCoreService,
        asignacion_core: "AsignacionCoreService",
        expediente_flujo: ExpedienteCreacionFlujo,
    ):
        self.solicitud_core = solicitud_core
        self.asignacion_core = asignacion_core
        self.expediente_flujo = expediente_flujo

    async def _proceso_crear_solicitud(
        self,
        data: SolicitudCreateIn,
        usuario_id: int,
    ) -> Solicitud:
        """
        Flujo para crear una solicitud con distribución de áreas de forma atómica.

        1. Valida que el expediente existe y no tiene solicitud.
        2. Crea la solicitud en estado REGISTRADA.
        3. Crea el historial de estado inicial.
        4. Si hay áreas, establece fecha_inicio_gestion y transiciona a EN_GESTION.
        5. Crea las asignaciones y períodos para cada área.
        6. Crea las notificaciones para cada área.

        Args:
            data: Schema SolicitudCreateIn con datos de la solicitud y áreas.
            usuario_id: ID del usuario que realiza el registro.

        Returns:
            Instancia de Solicitud creada con sus asignaciones.

        Raises:
            HttpError: Si el expediente no existe o ya tiene solicitud.
        """
        solicitud = await sync_to_async(self._creacion_atomica)(
            data=data,
            usuario_id=usuario_id,
        )
        return solicitud

    @transaction.atomic()
    def _creacion_atomica(
        self,
        data: SolicitudCreateIn,
        usuario_id: int,
    ) -> Solicitud:
        """
        Creación atómica de solicitud + historial + asignaciones + notificaciones.

        @transaction.atomic() garantiza que si falla cualquier operación,
        se revierte todo.
        """
        # 1. Validar expediente existe y no tiene solicitud
        expediente = self.solicitud_core._obtener_expediente_para_solicitud(
            data.expediente_id
        )
        if expediente is None:
            raise HttpError(404, f"Expediente '{data.expediente_id}' no encontrado")

        if hasattr(expediente, "solicitud") and expediente.solicitud is not None:
            raise HttpError(
                409,
                f"El expediente '{data.expediente_id}' ya tiene una solicitud asociada",
            )

        # 2. Crear la solicitud en estado REGISTRADA
        ahora = datetime.now()
        solicitud = self.solicitud_core._crear_solicitud(
            expediente=expediente,
            estado=EstadoSolicitud.REGISTRADA,
            prioridad=data.prioridad,
            fecha_registro=ahora,
            observacion=data.observacion,
            creado_por_id=usuario_id,
        )

        # 3. Crear historial de estado inicial (estado_anterior=None -> REGISTRADA)
        self.solicitud_core._crear_historial_estado(
            solicitud=solicitud,
            estado_anterior=None,
            estado_nuevo=EstadoSolicitud.REGISTRADA,
            cambiado_por_id=usuario_id,
            fecha_cambio=ahora,
            motivo="Creación de solicitud",
            origen=OrigenCambio.CREACION,
        )

        # 4. Si hay áreas, establecer fecha_inicio_gestion y transicionar a EN_GESTION
        if data.areas_distribucion:
            ahora = datetime.now()
            solicitud.fecha_inicio_gestion = ahora
            solicitud.estado = EstadoSolicitud.EN_GESTION
            solicitud.save()
            # Crear historial global: REGISTRADA → EN_GESTION
            self.solicitud_core._crear_historial_estado(
                solicitud=solicitud,
                estado_anterior=EstadoSolicitud.REGISTRADA,
                estado_nuevo=EstadoSolicitud.EN_GESTION,
                cambiado_por_id=usuario_id,
                fecha_cambio=ahora,
                motivo="Inicio de gestión con primera área",
                origen=OrigenCambio.CAMBIO_ESTADO,
            )

        # 5. Crear asignaciones y notificaciones por cada área
        for area_distribucion in data.areas_distribucion:
            # Verificar que el área existe
            try:
                area = Area.objects.get(id=area_distribucion.area_id)
            except Area.DoesNotExist:
                raise HttpError(
                    404,
                    f"Área '{area_distribucion.area_id}' no encontrada",
                )

            # Crear SolicitudAsignacion y SolicitudAsignacionPeriodo (ciclo=1, PENDIENTE)
            asignacion, periodo = self.asignacion_core._crear_asignacion_con_periodo_inicial(
                solicitud=solicitud,
                area=area,
                tipo_participacion=area_distribucion.tipo_participacion,
                observacion=area_distribucion.observacion,
                incorporado_por_id=usuario_id,
                fecha_incorporacion=ahora,
                numero_ciclo=1,
                estado_periodo=EstadoPeriodo.PENDIENTE,
                fecha_inicio=ahora,
                iniciado_por_id=usuario_id,
            )

            # Crear notificación para el área (con período enlazado)
            self._crear_notificacion_nueva_asignacion(
                area=area,
                solicitud=solicitud,
                asignacion=asignacion,
                periodo=periodo,
                generado_por_id=usuario_id,
                fecha_evento=ahora,
            )

        return solicitud

    async def _proceso_crear_hibrido(
        self,
        payload: SolicitudHibridaCreateIn,
        usuario_id: int,
    ) -> Solicitud:
        """
        Flujo para crear un expediente y solicitud de forma atómica.
        """
        solicitud = await sync_to_async(self._creacion_hibrida_atomica)(
            payload=payload,
            usuario_id=usuario_id,
        )
        return solicitud

    @transaction.atomic()
    def _creacion_hibrida_atomica(
        self,
        payload: SolicitudHibridaCreateIn,
        usuario_id: int,
    ) -> Solicitud:
        """
        Creación atómica de expediente + solicitud + historial + asignaciones + notificaciones.
        """
        ahora = datetime.now()

        # a) Crear el expediente
        expediente = self.expediente_flujo._creacion_atomica(
            data=payload.expediente,
            usuario_id=usuario_id,
        )

        # Reload with prefetch so present_list_item avoids a lazy query on exp.archivos.all()
        expediente = Expediente.objects.prefetch_related("archivos").get(pk=expediente.pk)

        # b) Crear la solicitud en estado REGISTRADA
        solicitud = self.solicitud_core._crear_solicitud(
            expediente=expediente,
            estado=EstadoSolicitud.REGISTRADA,
            prioridad=payload.prioridad,
            fecha_registro=ahora,
            observacion=payload.observacion,
            creado_por_id=usuario_id,
        )

        # c) Registrar cambio de estado inicial
        self.solicitud_core._crear_historial_estado(
            solicitud=solicitud,
            estado_anterior=None,
            estado_nuevo=EstadoSolicitud.REGISTRADA,
            cambiado_por_id=usuario_id,
            fecha_cambio=ahora,
            motivo="Creación de solicitud híbrida",
            origen=OrigenCambio.CREACION,
        )

        # d) Si hay áreas, establecer fecha_inicio_gestion y transicionar a EN_GESTION
        if payload.areas_distribucion:
            ahora = datetime.now()
            solicitud.fecha_inicio_gestion = ahora
            solicitud.estado = EstadoSolicitud.EN_GESTION
            solicitud.save()
            self.solicitud_core._crear_historial_estado(
                solicitud=solicitud,
                estado_anterior=EstadoSolicitud.REGISTRADA,
                estado_nuevo=EstadoSolicitud.EN_GESTION,
                cambiado_por_id=usuario_id,
                fecha_cambio=ahora,
                motivo="Inicio de gestión con primera área",
                origen=OrigenCambio.CAMBIO_ESTADO,
            )

        # e) Crear asignaciones y notificaciones por cada área
        for area_distribucion in payload.areas_distribucion:
            try:
                area = Area.objects.get(id=area_distribucion.area_id)
            except Area.DoesNotExist:
                raise HttpError(
                    404,
                    f"Área '{area_distribucion.area_id}' no encontrada",
                )

            asignacion, periodo = self.asignacion_core._crear_asignacion_con_periodo_inicial(
                solicitud=solicitud,
                area=area,
                tipo_participacion=area_distribucion.tipo_participacion,
                observacion=area_distribucion.observacion,
                incorporado_por_id=usuario_id,
                fecha_incorporacion=ahora,
                numero_ciclo=1,
                estado_periodo=EstadoPeriodo.PENDIENTE,
                fecha_inicio=ahora,
                iniciado_por_id=usuario_id,
            )

            self._crear_notificacion_nueva_asignacion(
                area=area,
                solicitud=solicitud,
                asignacion=asignacion,
                periodo=periodo,
                generado_por_id=usuario_id,
                fecha_evento=ahora,
            )

        # f) Crear ExpedienteAntecedente para cada antecedente
        for ant_data in payload.antecedentes:
            self._crear_antecedente(
                expediente=expediente,
                antecedente_id=ant_data.antecedente_id,
                categoria=ant_data.categoria,
                observaciones=ant_data.observaciones,
            )

        # g) Retornar la Solicitud
        return solicitud

    def _crear_notificacion_nueva_asignacion(
        self,
        area,
        solicitud,
        asignacion,
        generado_por_id: int,
        fecha_evento: datetime,
        periodo=None,
    ) -> Notificacion:
        """
        Crea una notificación de nueva asignación para el área.

        También materializa NotificacionUsuario para cada usuario activo del área.

        Args:
            area: Instancia de Area.
            solicitud: Instancia de Solicitud.
            asignacion: Instancia de SolicitudAsignacion.
            generado_por_id: ID del usuario que genera la notificación.
            fecha_evento: Fecha y hora del evento.
            periodo: Instancia de SolicitudAsignacionPeriodo (opcional).

        Returns:
            Instancia de Notificacion creada.
        """
        from modules.asignaciones.domain.models.notificacion import NotificacionUsuario

        notificacion = Notificacion.objects.create(
            area=area,
            tipo=TipoNotificacion.NUEVA_ASIGNACION,
            solicitud=solicitud,
            asignacion=asignacion,
            periodo=periodo,
            titulo=f"Nueva asignación - Expediente {solicitud.expediente.id_publico}",
            mensaje=f"Se le ha asignado el expediente {solicitud.expediente.id_publico} para su atención.",
            generada_por_id=generado_por_id,
            fecha_evento=fecha_evento,
            estado=EstadoNotificacion.PENDIENTE,
        )

        # Materializar NotificacionUsuario para cada usuario con asignación vigente al área.
        User = get_user_model()
        usuarios_area = User.objects.filter(
            asignaciones__area=area,
            asignaciones__periodo_fin__isnull=True,
            is_active=True,
        ).distinct()
        for usuario in usuarios_area:
            NotificacionUsuario.objects.create(
                notificacion=notificacion,
                usuario=usuario,
            )

        return notificacion

    def _crear_antecedente(
        self,
        expediente: "Expediente",
        antecedente_id: "UUID",
        categoria: str | None,
        observaciones: str | None,
    ) -> "ExpedienteAntecedente":
        """
        Vincula un expediente antecedente al expediente recién creado.

        Args:
            expediente: Instancia del expediente nuevo.
            antecedente_id: UUID del expediente antecedente.
            categoria: Categoría del vínculo (opcional).
            observaciones: Observaciones sobre el vínculo (opcional).

        Returns:
            Instancia de ExpedienteAntecedente creada.

        Raises:
            HttpError: Si el antecedente no existe.
        """
        from modules.tramites.domain.models import ExpedienteAntecedente

        try:
            antecedente = Expediente.objects.get(id=antecedente_id)
        except Expediente.DoesNotExist:
            raise HttpError(
                404,
                f"Expediente antecedente '{antecedente_id}' no encontrado",
            )

        return ExpedienteAntecedente.objects.create(
            expediente=expediente,
            antecedente=antecedente,
            categoria=categoria,
            observaciones=observaciones,
        )


class SolicitudAreaOperacionesFlujo:
    """
    Flujo asíncrono para operaciones sobre áreas de una Solicitud existente.

    Operaciones:
    - Incorporar área: agrega un área nueva a una solicitud existente.

    El @transaction.atomic() garantiza atomicidad en la creación de
    asignación + período + notificación + transición de estado.
    """

    @inject
    def __init__(
        self,
        solicitud_core: SolicitudCoreService,
        asignacion_core: "AsignacionCoreService",
        creacion_flujo: "SolicitudCreacionFlujo",
    ):
        self.solicitud_core = solicitud_core
        self.asignacion_core = asignacion_core
        self.creacion_flujo = creacion_flujo

    async def _proceso_incorporar_area(
        self,
        solicitud_id: "UUID",
        area_id: "UUID",
        tipo_participacion: str,
        observacion: str | None,
        usuario_id: int,
    ) -> "Solicitud":
        """
        Incorpora un área a una solicitud existente.

        1. Valida que la Solicitud existe y está en estado válido.
        2. Valida que el Área existe y no está ya asignada.
        3. Crea SolicitudAsignacion + SolicitudAsignacionPeriodo (ciclo 1, PENDIENTE).
        4. Si la solicitud estaba en REGISTRADA → transiciona a EN_GESTION,
           establece fecha_inicio_gestion.
        5. Crea la notificación para el área.

        Args:
            solicitud_id: UUID de la Solicitud.
            area_id: UUID del Área a incorporar.
            tipo_participacion: PRINCIPAL o ADJUNTA.
            observacion: Observación opcional.
            usuario_id: ID del usuario que realiza la operación.

        Returns:
            Instancia de Solicitud actualizada.

        Raises:
            HttpError: Si la solicitud no existe, el área no existe,
                       o el área ya está asignada.
        """
        return await sync_to_async(self._incorporar_area_atomica)(
            solicitud_id=solicitud_id,
            area_id=area_id,
            tipo_participacion=tipo_participacion,
            observacion=observacion,
            usuario_id=usuario_id,
        )

    @transaction.atomic()
    def _incorporar_area_atomica(
        self,
        solicitud_id: "UUID",
        area_id: "UUID",
        tipo_participacion: str,
        observacion: str | None,
        usuario_id: int,
    ) -> "Solicitud":
        """
        Versión síncrona con @transaction.atomic para incorporar área.
        """
        from uuid import UUID
        from modules.tramites.domain.models import Solicitud
        from modules.usuarios.domain.models import Area
        from modules.tramites.domain.constants import EstadoSolicitud
        from modules.tramites.domain.models.solicitud_historial import OrigenCambio
        from modules.asignaciones.domain.models import SolicitudAsignacion
        from modules.asignaciones.domain.constants import EstadoPeriodo

        ahora = datetime.now()

        # 1. Obtener la Solicitud con lock
        try:
            solicitud = Solicitud.objects.select_for_update().get(id=solicitud_id)
        except Solicitud.DoesNotExist:
            raise HttpError(404, f"Solicitud '{solicitud_id}' no encontrada")

        # 2. Validar estado de la solicitud (no puede estar FINALIZADA ni ANULADA)
        if solicitud.estado in (EstadoSolicitud.FINALIZADA, EstadoSolicitud.ANULADA):
            raise HttpError(
                409,
                f"No se puede incorporar áreas a una solicitud en estado {solicitud.estado}",
            )

        # 3. Obtener el Área
        try:
            area = Area.objects.get(id=area_id)
        except Area.DoesNotExist:
            raise HttpError(404, f"Área '{area_id}' no encontrada")

        # 4. Verificar que el área no esté ya asignada
        if SolicitudAsignacion.objects.filter(solicitud=solicitud, area=area).exists():
            raise HttpError(
                409,
                f"El área '{area.nombre}' ya está asignada a esta solicitud",
            )

        # 5. Crear SolicitudAsignacion + SolicitudAsignacionPeriodo
        asignacion, periodo = self.asignacion_core._crear_asignacion_con_periodo_inicial(
            solicitud=solicitud,
            area=area,
            tipo_participacion=tipo_participacion,
            observacion=observacion,
            incorporado_por_id=usuario_id,
            fecha_incorporacion=ahora,
            numero_ciclo=1,
            estado_periodo=EstadoPeriodo.PENDIENTE,
            fecha_inicio=ahora,
            iniciado_por_id=usuario_id,
        )

        # 6. Si estaba en REGISTRADA → transicionar a EN_GESTION
        if solicitud.estado == EstadoSolicitud.REGISTRADA:
            solicitud.estado = EstadoSolicitud.EN_GESTION
            solicitud.fecha_inicio_gestion = ahora
            solicitud.save()
            # Historial: REGISTRADA → EN_GESTION
            self.solicitud_core._crear_historial_estado(
                solicitud=solicitud,
                estado_anterior=EstadoSolicitud.REGISTRADA,
                estado_nuevo=EstadoSolicitud.EN_GESTION,
                cambiado_por_id=usuario_id,
                fecha_cambio=ahora,
                motivo="Incorporación de primera área",
                origen=OrigenCambio.CAMBIO_ESTADO,
            )

        # 7. Crear notificación
        self.creacion_flujo._crear_notificacion_nueva_asignacion(
            area=area,
            solicitud=solicitud,
            asignacion=asignacion,
            periodo=periodo,
            generado_por_id=usuario_id,
            fecha_evento=ahora,
        )

        return solicitud
