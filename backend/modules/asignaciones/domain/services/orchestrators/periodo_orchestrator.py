"""
PeriodoOrchestrator — fachada asíncrona ligera para controladores de Período.

Delegación de operaciones a PeriodoOperacionesFlujo.
Async-first (contrato P3) — arquitectura establecida del proyecto.
"""
from uuid import UUID

from asgiref.sync import sync_to_async
from injector import inject

from ninja.errors import HttpError

from modules.asignaciones.domain.models import (
    SolicitudAsignacionPeriodo,
    SolicitudAsignacionRespuesta,
)
from modules.asignaciones.domain.services.flujos.periodo_flujo import (
    PeriodoOperacionesFlujo,
)


class PeriodoOrchestrator:
    """
    Fachada asíncrona ligera — delega operaciones de período a PeriodoOperacionesFlujo.
    """

    @inject
    def __init__(self, periodo_operaciones_flujo: PeriodoOperacionesFlujo):
        self.periodo_operaciones_flujo = periodo_operaciones_flujo

    async def iniciar_gestion(
        self,
        periodo_id: UUID,
        usuario_id: int,
    ):
        """
        Inicia la gestión de un período en estado PENDIENTE.

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.
            usuario_id: ID del usuario que inicia la gestión.

        Returns:
            Instancia de SolicitudAsignacionPeriodo con relaciones precargadas.
        """
        return await self.periodo_operaciones_flujo._proceso_iniciar_gestion(
            periodo_id=periodo_id,
            usuario_id=usuario_id,
        )

    async def tomar_periodo(
        self,
        periodo_id: UUID,
        usuario_id: int,
    ):
        """
        El usuario toma un período: se asigna a sí mismo como participante
        y transiciona el período de PENDIENTE a EN_GESTION.

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.
            usuario_id: ID del usuario que toma el período.

        Returns:
            Instancia de SolicitudAsignacionPeriodo con relaciones precargadas.
        """
        return await self.periodo_operaciones_flujo._proceso_tomar_periodo(
            periodo_id=periodo_id,
            usuario_id=usuario_id,
        )

    async def obtener_periodo(self, periodo_id: UUID):
        """
        Obtiene un período con sus relaciones precargadas.

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.

        Returns:
            Instancia de SolicitudAsignacionPeriodo o None si no existe.
        """
        def _query():
            try:
                return (
                    SolicitudAsignacionPeriodo.objects
                    .select_related(
                        "asignacion__solicitud__expediente",
                        "asignacion__area",
                    )
                    .prefetch_related(
                        "historial_estados",
                        "usuarios__usuario",
                    )
                    .get(id=periodo_id)
                )
            except SolicitudAsignacionPeriodo.DoesNotExist:
                return None

        return await sync_to_async(_query, thread_sensitive=True)()

    async def agregar_usuario_periodo(
        self,
        periodo_id: UUID,
        usuario_id: UUID,
        usuario_a_asignar_id: UUID,
        rol: str | None = None,
    ):
        """
        Asigna un usuario como participante a un período existente.

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.
            usuario_id: UUID del usuario que realiza la asignación.
            usuario_a_asignar_id: UUID del usuario a asignar como participante.
            rol: Rol del participante (default "Responsable").

        Returns:
            Instancia de SolicitudAsignacionPeriodo con relaciones precargadas.
        """
        return await self.periodo_operaciones_flujo._proceso_agregar_usuario(
            periodo_id=periodo_id,
            usuario_id=usuario_id,
            usuario_a_asignar_id=usuario_a_asignar_id,
            rol=rol,
        )

    async def finalizar_periodo(
        self,
        periodo_id: UUID,
        usuario_id: int,
        tipo_cierre: str | None = None,
        motivo_cierre: str | None = None,
        observacion: str | None = None,
    ):
        """
        Finaliza un período de asignación, transicionándolo a CERRADO.

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.
            usuario_id: ID del usuario que finaliza el período.
            tipo_cierre: Tipo de cierre (default FINALIZADO).
            motivo_cierre: Motivo opcional del cierre.
            observacion: Observación opcional.

        Returns:
            Instancia de SolicitudAsignacionPeriodo con relaciones precargadas.
        """
        return await self.periodo_operaciones_flujo._proceso_finalizar(
            periodo_id=periodo_id,
            usuario_id=usuario_id,
            tipo_cierre=tipo_cierre,
            motivo_cierre=motivo_cierre,
            observacion=observacion,
        )

    async def marcar_asignacion_erronea(
        self,
        periodo_id: UUID,
        usuario_id: int,
        motivo_cierre: str | None = None,
        observacion: str | None = None,
    ):
        """
        Marca un período como asignación errónea, transicionándolo a CERRADO
        con tipo_cierre=ASIGNACION_ERRONEA.

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.
            usuario_id: ID del usuario que marca la asignación como errónea.
            motivo_cierre: Motivo opcional del cierre.
            observacion: Observación opcional.

        Returns:
            Instancia de SolicitudAsignacionPeriodo con relaciones precargadas.
        """
        return await self.periodo_operaciones_flujo._proceso_marcar_erronea(
            periodo_id=periodo_id,
            usuario_id=usuario_id,
            motivo_cierre=motivo_cierre,
            observacion=observacion,
        )

    async def cambiar_participacion(
        self,
        periodo_id: UUID,
        usuario_id: int,
        nuevo_tipo: str,
    ):
        """
        Cambia el tipo de participación de un período (PRINCIPAL ↔ ADJUNTA).

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.
            usuario_id: ID del usuario que ejecuta el cambio.
            nuevo_tipo: Nuevo tipo de participación (PRINCIPAL o ADJUNTA).

        Returns:
            Instancia de SolicitudAsignacionPeriodo con relaciones precargadas.
        """
        return await self.periodo_operaciones_flujo._proceso_cambiar_participacion(
            periodo_id=periodo_id,
            usuario_id=usuario_id,
            nuevo_tipo=nuevo_tipo,
        )

    async def crear_respuesta_borrador(
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

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.
            usuario_id: ID del usuario que crea la respuesta.
            tipo_respuesta: Tipo de respuesta (INFORME, OBSERVACION, etc.).
            contenido: Contenido o texto de la respuesta (opcional).
            archivo: Ruta del archivo adjunto (opcional).
            observacion: Observación adicional (opcional).

        Returns:
            Instancia de SolicitudAsignacionRespuesta creada en estado BORRADOR.
        """
        return await self.periodo_operaciones_flujo._proceso_crear_respuesta_borrador(
            periodo_id=periodo_id,
            usuario_id=usuario_id,
            tipo_respuesta=tipo_respuesta,
            contenido=contenido,
            archivo=archivo,
            observacion=observacion,
        )

    async def listar_respuestas(self, periodo_id: UUID):
        """
        Lista las respuestas de un período, ordenadas por created_at descendente.

        Args:
            periodo_id: UUID del SolicitudAsignacionPeriodo.

        Returns:
            Lista de instancias de SolicitudAsignacionRespuesta del período.

        Raises:
            HttpError: 404 si el período no existe.
        """
        def _query():
            # Validar que el período existe
            try:
                SolicitudAsignacionPeriodo.objects.get(id=periodo_id)
            except SolicitudAsignacionPeriodo.DoesNotExist:
                raise HttpError(404, f"Período '{periodo_id}' no encontrado")

            return list(
                SolicitudAsignacionRespuesta.objects
                .filter(periodo_id=periodo_id)
                .order_by("-created_at")
            )

        return await sync_to_async(_query, thread_sensitive=True)()

    async def emitir_respuesta(
        self,
        respuesta_id: UUID,
        usuario_id: int,
    ):
        """
        Emite una respuesta que se encuentra en estado BORRADOR.

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
        return await self.periodo_operaciones_flujo._proceso_emitir_respuesta(
            respuesta_id=respuesta_id,
            usuario_id=usuario_id,
        )

    async def anular_respuesta(
        self,
        respuesta_id: UUID,
        usuario_id: int,
    ):
        """
        Anula una respuesta que se encuentra en estado EMITIDA.

        Args:
            respuesta_id: UUID de la SolicitudAsignacionRespuesta.
            usuario_id: ID del usuario que anula la respuesta.

        Returns:
            Instancia de SolicitudAsignacionRespuesta en estado ANULADA.

        Raises:
            HttpError: 404 si la respuesta no existe.
                       400 si la respuesta no está en estado EMITIDA.
        """
        return await self.periodo_operaciones_flujo._proceso_anular_respuesta(
            respuesta_id=respuesta_id,
            usuario_id=usuario_id,
        )

    async def rectificar_respuesta(
        self,
        respuesta_id: UUID,
        usuario_id: int,
    ):
        """
        Rectifica una respuesta que se encuentra en estado EMITIDA.

        Args:
            respuesta_id: UUID de la SolicitudAsignacionRespuesta.
            usuario_id: ID del usuario que rectifica la respuesta.

        Returns:
            Instancia de SolicitudAsignacionRespuesta en estado RECTIFICADA.

        Raises:
            HttpError: 404 si la respuesta no existe.
                       400 si la respuesta no está en estado EMITIDA.
        """
        return await self.periodo_operaciones_flujo._proceso_rectificar_respuesta(
            respuesta_id=respuesta_id,
            usuario_id=usuario_id,
        )
