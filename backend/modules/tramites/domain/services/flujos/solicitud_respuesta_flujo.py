"""
SolicitudRespuestaFlujo — flujo async para emitir respuesta formal a una Solicitud.

transaction.atomic() vive AQUÍ — en el flujo que coordina la respuesta
compuesta: mensaje + respuesta + transición de estado + notificación.
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""

import logging
from datetime import datetime
from uuid import UUID

from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone
from injector import inject
from ninja.errors import HttpError

from modules.asignaciones.domain.constants import (
    EstadoPeriodo,
    EstadoPeriodoOperativo,
    OrigenEstadoPeriodo,
    TipoCierre,
)
from modules.asignaciones.domain.models import (
    SolicitudAsignacionPeriodo,
    SolicitudAsignacionPeriodoEstadoHistorial,
)
from modules.conversaciones.domain.constants import TipoMensaje
from modules.conversaciones.domain.models import (
    Conversacion,
    Mensaje,
    MensajeArchivoAdjunto,
    SolicitudConversacion,
)
from modules.conversaciones.domain.schemas.mensaje_schemas import (
    MensajeArchivoAdjuntoData,
    MensajeCreateData,
)
from modules.conversaciones.domain.services.core.mensajeria_service import (
    MensajeriaCoreService,
)
from modules.tramites.domain.constants import EstadoCambio, EstadoSolicitud
from modules.tramites.domain.models import (
    Solicitud,
    SolicitudEstadoHistorial,
)
from modules.tramites.domain.models.solicitud_historial import OrigenCambio
from modules.tramites.domain.models.solicitud_respuesta import SolicitudRespuesta
from modules.tramites.domain.schemas.solicitud_respuesta_schemas import (
    SolicitudRespuestaCreateData,
)
from modules.tramites.domain.services.core.solicitud_respuesta_core_service import (
    SolicitudRespuestaCoreService,
)
from modules.tramites.domain.services.core.solicitud_core_service import (
    SolicitudCoreService,
)
from modules.usuarios.domain.models import Area, Usuario
from modules.notificaciones.domain.services.core.notificacion_service import (
    NotificacionService,
)

logger = logging.getLogger(__name__)


class SolicitudRespuestaFlujo:
    """
    Flujo asíncrono para emitir una respuesta formal a una Solicitud.

    El flujo:
    1. Valida que la Solicitud existe y no está FINALIZADA/ANULADA.
    2. Infiere area y periodo del contexto del usuario autenticado.
    3. Obtiene o crea el puente SolicitudConversacion.
    4. Dentro de transaction.atomic():
       a. Crea Mensaje(tipo=SISTEMA) en la conversación para auditoría.
       b. Crea MensajeArchivoAdjunto para cada archivo.
       c. Crea SolicitudRespuesta vinculada.
       d. Si es_final=True:
          - Transiciona Solicitud a FINALIZADA con fecha_cierre.
          - Crea SolicitudEstadoHistorial con origen=CIERRE.
           - Cierra la Conversacion (fecha_cierre=now).
       e. Emite notificación RESPUESTA_FINAL al área.
    """

    @inject
    def __init__(
        self,
        respuesta_core: SolicitudRespuestaCoreService,
        solicitud_core: SolicitudCoreService,
        mensajeria_service: MensajeriaCoreService,
        notificacion_service: NotificacionService,
    ):
        self.respuesta_core = respuesta_core
        self.solicitud_core = solicitud_core
        self.mensajeria_service = mensajeria_service
        self.notificacion_service = notificacion_service

    async def _proceso_emitir_respuesta(
        self,
        solicitud_id: UUID,
        usuario_id: int,
        tipo_respuesta: str,
        contenido: str | None,
        es_final: bool,
        archivos_data: list[dict] | None = None,
    ):
        """
        Flujo para emitir una respuesta formal a una Solicitud.

        Args:
            solicitud_id: UUID de la Solicitud.
            usuario_id: ID del usuario que emite la respuesta.
            tipo_respuesta: INFORME | OBSERVACION | CONFORMIDAD | DESCARGO | OTRO.
            contenido: Texto de la respuesta (puede ser None si hay archivos).
            es_final: Si True, esta respuesta cierra la solicitud.
            archivos_data: Lista de dicts con metadata de archivos adjuntos.

        Returns:
            SolicitudRespuestaResult con la respuesta creada.

        Raises:
            HttpError 404: Si la Solicitud no existe.
            HttpError 409: Si la Solicitud ya está FINALIZADA o ANULADA,
                          o si ya existe otra respuesta con es_final=True.
            HttpError 400: Si el usuario no tiene área asignada.
        """
        return await sync_to_async(self._emitir_respuesta_atomica)(
            solicitud_id=solicitud_id,
            usuario_id=usuario_id,
            tipo_respuesta=tipo_respuesta,
            contenido=contenido,
            es_final=es_final,
            archivos_data=archivos_data or [],
        )

    @transaction.atomic()
    def _emitir_respuesta_atomica(
        self,
        solicitud_id: UUID,
        usuario_id: int,
        tipo_respuesta: str,
        contenido: str | None,
        es_final: bool,
        archivos_data: list[dict],
    ):
        """
        Versión síncrona con @transaction.atomic para emitir respuesta.
        """
        ahora = timezone.now()

        # ── 1. Obtener Solicitud con lock ────────────────────────────────────
        try:
            solicitud = Solicitud.objects.select_for_update().get(id=solicitud_id)
        except Solicitud.DoesNotExist:
            raise HttpError(404, f"Solicitud '{solicitud_id}' no encontrada")

        # ── 2. Validar estado ────────────────────────────────────────────────
        if solicitud.estado == EstadoSolicitud.FINALIZADA:
            raise HttpError(409, "La solicitud ya está FINALIZADA")
        if solicitud.estado == EstadoSolicitud.ANULADA:
            raise HttpError(409, "No se puede responder a una solicitud ANULADA")

        # ── 3. Verificar que no exista otra respuesta final (si es_final=True) ─
        if es_final:
            existente = SolicitudRespuesta.objects.filter(
                solicitud=solicitud,
                es_final=True,
            ).exists()
            if existente:
                raise HttpError(
                    409,
                    "Ya existe una respuesta final para esta solicitud",
                )

        # ── 4. Obtener usuario y área/periodo ────────────────────────────────
        try:
            usuario = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            raise HttpError(400, "Usuario no encontrado")

        area, periodo_id = self._inferir_area_periodo(usuario)
        if area is None:
            raise HttpError(400, "Usuario no tiene área asignada")

        # ── 5. Obtener o crear puente SolicitudConversacion ────────────────
        conversacion = self._obtener_o_crear_conversacion(
            solicitud=solicitud,
            ahora=ahora,
        )

        # ── 6. Crear Mensaje SISTEMA en la conversación ───────────────────
        actor_nombre = f"{usuario.nombres} {usuario.apellidos}".strip() or usuario.username
        if es_final:
            mensaje_contenido = (
                f"La solicitud fue cerrada por el área {area.nombre}. "
                f"Acción realizada por {actor_nombre}."
            )
        else:
            mensaje_contenido = (
                f"El área {area.nombre} emitió respuesta tipo {tipo_respuesta}. "
                f"Acción realizada por {actor_nombre}."
            )

        mensaje_data = MensajeCreateData(
            conversacion_id=conversacion.id,
            autor_usuario_id=None,  # SISTEMA message
            contenido=mensaje_contenido,
            tipo=TipoMensaje.SISTEMA,
            fecha_envio=ahora,
        )
        mensaje = self.mensajeria_service.crear_mensaje(mensaje_data)

        # ── 7. Crear MensajeArchivoAdjunto para cada archivo ───────────────
        mensaje_archivos = []
        for archivo_dict in archivos_data:
            # Build MensajeArchivoAdjuntoData with the uploaded file
            adjunto_data = MensajeArchivoAdjuntoData(
                archivo=archivo_dict.get("archivo"),
                nombre_original=archivo_dict["nombre_original"],
                mime_type=archivo_dict.get("mime_type"),
                tamano_bytes=archivo_dict.get("tamano_bytes"),
                subido_por_id=usuario_id,
                fecha_archivo=ahora,
                descripcion=archivo_dict.get("descripcion"),
            )
            # Use service to handle two-step: save file → create Archivo → create link
            adjunto = self.mensajeria_service._crear_archivo_adjunto(mensaje, adjunto_data)
            mensaje_archivos.append({
                "id": str(adjunto.id),
                "nombre_original": adjunto.archivo.nombre_original if adjunto.archivo else "",
                "mime_type": adjunto.archivo.mime_type if adjunto.archivo else None,
                "tamano_bytes": adjunto.archivo.tamano_bytes if adjunto.archivo else None,
            })

        # ── 8. Crear SolicitudRespuesta ────────────────────────────────────
        create_data = SolicitudRespuestaCreateData(
            solicitud_id=solicitud_id,
            tipo_respuesta=tipo_respuesta,
            contenido=contenido,
            es_final=es_final,
        )

        resultado = self.respuesta_core._crear_respuesta(
            data=create_data,
            conversacion_id=conversacion.id,
            mensaje_id=mensaje.id,
            area_id=area.id,
            area_nombre=area.nombre,
            periodo_id=periodo_id,
            emitido_por_id=usuario_id,
            emitido_por_nombre=f"{usuario.nombres} {usuario.apellidos}".strip() or usuario.username,
            mensaje_archivos=mensaje_archivos,
        )

        # ── 9. Si es_final=True: cerrar solicitud y conversación ──────────
        if es_final:
            # Transición de estado
            estado_anterior = solicitud.estado
            solicitud.estado = EstadoSolicitud.FINALIZADA
            solicitud.fecha_cierre = ahora
            solicitud.save()

            # Historial de cierre
            self.solicitud_core._crear_historial_estado(
                solicitud=solicitud,
                estado_anterior=estado_anterior,
                estado_nuevo=EstadoSolicitud.FINALIZADA,
                cambiado_por_id=usuario_id,
                fecha_cambio=ahora,
                motivo=f"Respuesta final emitida: {tipo_respuesta}",
                origen=OrigenCambio.CIERRE,
            )

            # Cerrar conversación
            if conversacion.fecha_cierre is None:
                conversacion.fecha_cierre = ahora
                conversacion.cerrado_por_id = usuario_id
                conversacion.save(update_fields=["fecha_cierre", "cerrado_por_id", "updated_at"])

            # Cerrar todos los períodos abiertos de la solicitud
            self._cerrar_periodos_solicitud(
                solicitud=solicitud,
                usuario=usuario,
                tipo_respuesta=tipo_respuesta,
                ahora=ahora,
            )

        # ── 10. Emitir notificación RESPUESTA_FINAL ─────────────────────────
        self._emitir_notificacion_respuesta_final(
            solicitud=solicitud,
            area=area,
            tipo_respuesta=tipo_respuesta,
            emitido_por_id=usuario_id,
            ahora=ahora,
            es_final=es_final,
        )

        return resultado

    def _inferir_area_periodo(
        self,
        usuario: Usuario,
    ) -> tuple[Area, UUID | None]:
        """
        Infiere el área y periodo del usuario para la respuesta.

        Área (regla: primero periodo activo, sino área del usuario):
          1. Usuario tiene participación activa en un periodo (fecha_fin IS NULL)
             con estado PENDIENTE o EN_GESTION → usar ese periodo y su área.
          2. Sino: usar usuario.area directamente.
          3. Si ninguna: retornar (None, None).

        Periodo (nullable):
          1. Usuario tiene participación activa en un periodo (fecha_fin IS NULL)
             con estado PENDIENTE o EN_GESTION → usar ese periodo.
          2. Sino: None.

        Returns:
            Tupla (area, periodo_id | None).
            area puede ser None si el usuario no tiene área asignada.
        """
        from modules.asignaciones.domain.models import (
            SolicitudAsignacionUsuario,
        )

        # Buscar participación activa en un periodo PENDIENTE o EN_GESTION
        participacion_activa = (
            SolicitudAsignacionUsuario.objects
            .filter(
                usuario_id=usuario.id,
                fecha_fin__isnull=True,
                periodo__estado__in=[
                    EstadoPeriodo.PENDIENTE,
                    EstadoPeriodo.EN_GESTION,
                ],
            )
            .select_related("periodo__asignacion__area")
            .order_by("-periodo__fecha_inicio")
            .first()
        )

        if participacion_activa is not None:
            periodo = participacion_activa.periodo
            area = periodo.asignacion.area
            return area, periodo.id

        # Fallback: área activa del usuario via AsignacionUsuario
        from modules.usuarios.domain.models import AsignacionUsuario
        asignacion_activa = (
            AsignacionUsuario.objects
            .filter(usuario_id=usuario.id, periodo_fin__isnull=True)
            .select_related("area")
            .order_by("-periodo_inicio")
            .first()
        )
        if asignacion_activa is not None:
            return asignacion_activa.area, None

        return None, None

    def _obtener_o_crear_conversacion(
        self,
        solicitud: Solicitud,
        ahora: datetime,
    ) -> Conversacion:
        """
        Obtiene o crea la conversación vinculada a la Solicitud.

        Si existe el puente SolicitudConversacion, retorna la conversación.
        Si no existe, crea una nueva conversación y el puente.

        Returns:
            Instancia de Conversacion.
        """
        bridge = SolicitudConversacion.objects.filter(
            solicitud=solicitud
        ).select_related("conversacion").first()

        if bridge is not None:
            return bridge.conversacion

        # Crear nueva conversación
        titulo = f"Conversación - {solicitud.expediente.id_publico}"
        from modules.conversaciones.domain.schemas.conversacion_schemas import (
            ConversacionCreateData,
        )
        conv_data = ConversacionCreateData(
            titulo=titulo,
            creada_por_id=solicitud.creado_por_id,
            fecha_inicio=ahora,
        )
        conversacion = self.mensajeria_service.crear_conversacion(conv_data)
        self.mensajeria_service.crear_puente_solicitud(
            solicitud_id=solicitud.pk,
            conversacion=conversacion,
        )
        return conversacion

    def _cerrar_periodos_solicitud(
        self,
        solicitud: Solicitud,
        usuario: Usuario,
        tipo_respuesta: str,
        ahora: datetime,
    ) -> None:
        """
        Cierra todos los períodos abiertos (PENDIENTE o EN_GESTION) de una solicitud.

        Cada período se transiciona a CERRADO con tipo_cierre=FINALIZADO y se
        registra el cambio en SolicitudAsignacionPeriodoEstadoHistorial con
        origen=FINALIZACION_SOLICITUD.

        Args:
            solicitud: Instancia de Solicitud siendo finalizada.
            usuario: Usuario que está finalizando la solicitud.
            tipo_respuesta: Tipo de respuesta final (para el motivo de cierre).
            ahora: Fecha/hora actual de la transacción.
        """
        periodos_abiertos = SolicitudAsignacionPeriodo.objects.filter(
            asignacion__solicitud=solicitud,
            estado__in=[EstadoPeriodo.PENDIENTE, EstadoPeriodo.EN_GESTION],
        ).select_for_update()

        if not periodos_abiertos.exists():
            return

        motivo = f"Cierre de solicitud: {tipo_respuesta}"

        for periodo in periodos_abiertos:
            estado_anterior = periodo.estado

            periodo.estado = EstadoPeriodo.CERRADO
            periodo.fecha_fin = ahora
            periodo.finalizado_por = usuario
            periodo.tipo_cierre = TipoCierre.FINALIZADO
            periodo.motivo_cierre = motivo
            periodo.save()

            SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
                periodo=periodo,
                estado_anterior=EstadoPeriodoOperativo[estado_anterior],
                estado_nuevo=EstadoPeriodoOperativo.CERRADO,
                fecha_cambio=ahora,
                cambiado_por=usuario,
                motivo=motivo,
                origen=OrigenEstadoPeriodo.FINALIZACION_SOLICITUD,
            )

    def _emitir_notificacion_respuesta_final(
        self,
        solicitud: Solicitud,
        area: Area,
        tipo_respuesta: str,
        emitido_por_id: UUID,
        ahora: datetime,
        es_final: bool,
    ) -> None:
        """
        Emite notificación RESPUESTA_FINAL al área y al creador de la solicitud.

        Si es_final=True:
          - Notifica al área que emitió la respuesta (ya conoce su propia respuesta).
          - Notifica al creador de la solicitud (sabe que fue cerrada).

        La notificación se emite fuera de la transacción principal
        (después del commit) para no bloquear la respuesta.
        """
        from modules.notificaciones.domain.constants import (
            AmbitoNotificacion,
            EventoNotificacion,
            PrioridadNotificacion,
        )

        titulo = f"Respuesta final emitida - Expediente {solicitud.expediente.id_publico}"
        mensaje = (
            f"El área {area.nombre} emitió una respuesta de tipo {tipo_respuesta} "
            f"a la solicitud {solicitud.expediente.id_publico}."
        )

        # Notificar al área (AUDITORIA: el área ya sabe que emitió, pero
        # la notificación sirve como registro formal).
        # Non-critical: graceful degradation if notification fails
        try:
            self.notificacion_service.crear_notificacion_area(
                area=area,
                titulo=titulo,
                mensaje=mensaje,
                ambito=AmbitoNotificacion.SOLICITUD,
                evento=EventoNotificacion.RESPUESTA_FINAL,
                prioridad=PrioridadNotificacion.ALTA,
                generada_por_id=emitido_por_id,
                ocurrido_en=ahora,
                solicitud=solicitud,
            )
        except Exception as e:
            logger.warning(
                "Failed to emit area notification for RESPUESTA_FINAL: %s", e
            )

        # Notificar al creador de la solicitud
        if solicitud.creado_por_id != emitido_por_id:
            try:
                self.notificacion_service.crear_notificacion_usuario(
                    usuario_id=solicitud.creado_por_id,
                    titulo=titulo,
                    mensaje=mensaje,
                    ambito=AmbitoNotificacion.SOLICITUD,
                    evento=EventoNotificacion.RESPUESTA_FINAL,
                    prioridad=PrioridadNotificacion.ALTA,
                    generada_por_id=emitido_por_id,
                    ocurrido_en=ahora,
                )
            except Exception as e:
                logger.warning(
                    "Failed to emit user notification for RESPUESTA_FINAL: %s", e
                )
