"""
ParticipacionUsuarioFlujo — flujo async para operaciones sobre participaciones de usuario.

Operation:
- Retirar usuario: marca fecha_fin, retirado_por, motivo_retiro en SolicitudAsignacionUsuario.

El @transaction.atomic() garantiza atomicidad en la actualización de la participación.
"""
from datetime import datetime
from uuid import UUID

from asgiref.sync import sync_to_async
from django.db import transaction
from injector import inject
from ninja.errors import HttpError

from modules.asignaciones.domain.models import (
    SolicitudAsignacionUsuario,
)
from modules.asignaciones.domain.constants import EstadoPeriodo


class ParticipacionUsuarioFlujo:
    """
    Flujo asíncrono para operaciones sobre participaciones de usuario en períodos.

    Operaciones:
    - Retirar: marca la participación como finalizada.
    """

    async def _proceso_retirar(
        self,
        participacion_id: UUID,
        usuario_id: UUID,
        motivo: str | None = None,
    ):
        """
        Retira a un usuario de una participación activa.

        1. Obtiene la participación (select_for_update).
        2. Valida que la participación existe (404).
        3. Valida que la participación está activa — fecha_fin IS NULL (409).
        4. Valida que el período asociado no está CERRADO (409).
        5. Establece fecha_fin, retirado_por y motivo_retiro.
        6. Retorna la Solicitud padre.

        Args:
            participacion_id: UUID del SolicitudAsignacionUsuario.
            usuario_id: UUID del usuario que retira la participación.
            motivo: Motivo opcional del retiro.

        Returns:
            Instancia de Solicitud (padre de la participación).

        Raises:
            HttpError: 404 si la participación no existe.
                       409 si la participación ya está inactive.
                       409 si el período está CERRADO.
        """
        return await sync_to_async(self._retirar_atomica)(
            participacion_id=participacion_id,
            usuario_id=usuario_id,
            motivo=motivo,
        )

    @transaction.atomic()
    def _retirar_atomica(
        self,
        participacion_id: UUID,
        usuario_id: UUID,
        motivo: str | None = None,
    ):
        """
        Versión síncrona con @transaction.atomic para retirar una participación.
        """
        from modules.usuarios.domain.models import Usuario

        ahora = datetime.now()

        # 1. Obtener la participación con lock
        try:
            participacion = (
                SolicitudAsignacionUsuario.objects
                .select_related("periodo__asignacion__solicitud")
                .select_for_update()
                .get(id=participacion_id)
            )
        except SolicitudAsignacionUsuario.DoesNotExist:
            raise HttpError(404, f"Participación '{participacion_id}' no encontrada")

        # 2. Validar que la participación está activa
        if participacion.fecha_fin is not None:
            raise HttpError(
                409,
                f"La participación ya está finalizada (fecha_fin: {participacion.fecha_fin})",
            )

        # 3. Validar que el período no está CERRADO
        if participacion.periodo.estado == EstadoPeriodo.CERRADO:
            raise HttpError(
                409,
                f"No se puede retirar un usuario de un período en estado {participacion.periodo.estado}",
            )

        # 4. Obtener el usuario que retira
        try:
            usuario = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            raise HttpError(404, f"Usuario '{usuario_id}' no encontrado")

        # 5. Marcar la participación como finalizada
        participacion.fecha_fin = ahora
        participacion.retirado_por = usuario
        participacion.motivo_retiro = motivo
        participacion.save()

        # 6. Retornar la Solicitud padre con relaciones precargadas
        return participacion.periodo.asignacion.solicitud
