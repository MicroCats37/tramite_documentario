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
from modules.asignaciones.domain.constants import EstadoPeriodo
from modules.notificaciones.domain.constants import (
    AmbitoNotificacion,
    EventoNotificacion,
    PrioridadNotificacion,
)
from modules.notificaciones.domain.models import Notificacion
from modules.notificaciones.domain.services.core.notificacion_service import (
    NotificacionService,
)
from modules.usuarios.domain.models import Area
from modules.conversaciones.domain.services.flujos.conversacion_flujo import (
    ConversacionFlujo,
)
from modules.conversaciones.domain.schemas.conversacion_schemas import (
    ConversacionCreateData,
)


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
        conversacion_flujo: "ConversacionFlujo",
        notificacion_service: NotificacionService,
    ):
        self.solicitud_core = solicitud_core
        self.asignacion_core = asignacion_core
        self.expediente_flujo = expediente_flujo
        self.conversacion_flujo = conversacion_flujo
        self.notificacion_service = notificacion_service

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

        # 4. Si hay áreas, transicionar a EN_TRAMITE (no a EN_GESTION).
        # EN_TRAMITE significa que las áreas fueron notificadas pero ningún período
        # está aún en gestión activa. fecha_inicio_gestion se setea recién cuando
        # el primer período transiciona a EN_GESTION (en periodo_flujo).
        if data.areas_distribucion:
            ahora = datetime.now()
            solicitud.estado = EstadoSolicitud.EN_TRAMITE
            solicitud.save()
            # Crear historial global: REGISTRADA → EN_TRAMITE
            self.solicitud_core._crear_historial_estado(
                solicitud=solicitud,
                estado_anterior=EstadoSolicitud.REGISTRADA,
                estado_nuevo=EstadoSolicitud.EN_TRAMITE,
                cambiado_por_id=usuario_id,
                fecha_cambio=ahora,
                motivo="Distribución de áreas — en trámite",
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

        # Crear conversación vinculada a la solicitud
        self._crear_conversacion_vinculada(
            solicitud=solicitud,
            usuario_id=usuario_id,
            ahora=ahora,
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

        # d) Si hay áreas, transicionar a EN_TRAMITE (no a EN_GESTION).
        # fecha_inicio_gestion se setea cuando el primer período inicia gestión activa.
        if payload.areas_distribucion:
            ahora = datetime.now()
            solicitud.estado = EstadoSolicitud.EN_TRAMITE
            solicitud.save()
            self.solicitud_core._crear_historial_estado(
                solicitud=solicitud,
                estado_anterior=EstadoSolicitud.REGISTRADA,
                estado_nuevo=EstadoSolicitud.EN_TRAMITE,
                cambiado_por_id=usuario_id,
                fecha_cambio=ahora,
                motivo="Distribución de áreas — en trámite",
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

        # g) Crear conversación vinculada a la solicitud
        self._crear_conversacion_vinculada(
            solicitud=solicitud,
            usuario_id=usuario_id,
            ahora=ahora,
        )

        # h) Retornar la Solicitud
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

        Delega en NotificacionService.crear_notificacion_area(...) que crea:
        - Notificacion (el evento central)
        - NotificacionArea (contexto de audiencia)
        - NotificacionSolicitud (contexto de solicitud, si se provee)
        - NotificacionAsignacion (contexto de asignación, si se provee)
        - NotificacionPeriodo (contexto de período, si se provee)
        - NotificacionUsuario para cada usuario elegible del área

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
        titulo = f"Nueva asignación - Expediente {solicitud.expediente.id_publico}"
        mensaje = (
            f"Se le ha asignado el expediente {solicitud.expediente.id_publico} "
            "para su atención."
        )

        notificacion = self.notificacion_service.crear_notificacion_area(
            area=area,
            titulo=titulo,
            mensaje=mensaje,
            ambito=AmbitoNotificacion.SOLICITUD,
            evento=EventoNotificacion.ASIGNACION_CREADA,
            prioridad=PrioridadNotificacion.NORMAL,
            generada_por_id=generado_por_id,
            ocurrido_en=fecha_evento,
            solicitud=solicitud,
            asignacion=asignacion,
            periodo=periodo,
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

    def _crear_conversacion_vinculada(
        self,
        solicitud: "Solicitud",
        usuario_id: int,
        ahora: datetime,
    ) -> None:
        """
        Crea una Conversacion vinculada a la Solicitud y el puente SolicitudConversacion.

        Se llama al final de _creacion_atomica y _creacion_hibrida_atomica, dentro
        del mismo transaction.atomic() que creó la solicitud, por lo que usa
        _crear_conversacion_atomica directamente (no el wrapper async) para evitar
        problemas de threading.

        El título de la conversación se construye con el id_publico del expediente
        asociado a la solicitud.

        Args:
            solicitud: Instancia de Solicitud recién creada.
            usuario_id: ID del usuario que crea la solicitud.
            ahora: Fecha/hora actual (recibida del caller para reuse).
        """
        titulo = f"Conversación - {solicitud.expediente.id_publico}"
        conv_data = ConversacionCreateData(
            titulo=titulo,
            creada_por_id=usuario_id,
            fecha_inicio=ahora,
        )
        # Se llama directamente la versión atómica sync (ya estamos en un
        # transaction.atomic), así Django anida la transacción correctamente.
        self.conversacion_flujo._crear_conversacion_atomica(
            data=conv_data,
            solicitud_id=solicitud.pk,
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

        # 6. Si estaba en REGISTRADA → transicionar a EN_TRAMITE.
        # No se setea fecha_inicio_gestion aquí — se setea cuando el primer
        # período inicia gestión activa (en periodo_flujo).
        if solicitud.estado == EstadoSolicitud.REGISTRADA:
            solicitud.estado = EstadoSolicitud.EN_TRAMITE
            solicitud.save()
            # Historial: REGISTRADA → EN_TRAMITE
            self.solicitud_core._crear_historial_estado(
                solicitud=solicitud,
                estado_anterior=EstadoSolicitud.REGISTRADA,
                estado_nuevo=EstadoSolicitud.EN_TRAMITE,
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
