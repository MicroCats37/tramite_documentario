"""
Esquemas HTTP request para Periodo — Schema Ninja para API.

Patrón 3: JSON Estricto (sin archivos).
"""
from uuid import UUID

from ninja import Field
from core.types import BaseSchema


class IniciarGestionIn(BaseSchema):
    """
    Payload para iniciar la gestión de un período.

    No requiere body — el ID del período viene en la URL.
    Se usa en POST /periodos/{periodo_id}/iniciar-gestion.
    """

    pass


class AgregarUsuarioPeriodoIn(BaseSchema):
    """
    Payload para agregar un usuario como participante a un período.

    Se usa en POST /periodos/{periodo_id}/usuarios.
    """

    usuario_id: UUID
    """ID del usuario a asignar como participante (UUID del Usuario)."""

    rol: str | None = None
    """Rol del participante (default 'Responsable')."""


class RetirarParticipacionIn(BaseSchema):
    """
    Payload opcional para retirar a un usuario de una participación.

    Se usa en POST /participaciones-usuario/{participacion_id}/retirar.
    El motivo es opcional.
    """

    motivo: str | None = Field(
        default=None,
        max_length=500,
        description="Motivo del retiro del usuario de la participación.",
    )


class FinalizarPeriodoIn(BaseSchema):
    """
    Payload para finalizar un período de asignación.

    Se usa en POST /periodos/{periodo_id}/finalizar.

    El tipo_cierre default es FINALIZADO. La observación es opcional.
    """

    tipo_cierre: str | None = Field(
        default="FINALIZADO",
        max_length=20,
        description="Tipo de cierre: FINALIZADO (default), DERIVADO, RECHAZADO, etc.",
    )

    motivo_cierre: str | None = Field(
        default=None,
        max_length=500,
        description="Motivo del cierre del período.",
    )

    observacion: str | None = Field(
        default=None,
        max_length=1000,
        description="Observación adicional al cerrar el período.",
    )


class MarcarAsignacionErroneaIn(BaseSchema):
    """
    Payload para marcar un período como asignación errónea.

    Se usa en POST /periodos/{periodo_id}/marcar-asignacion-erronea.

    El tipo_cierre es ASIGNACION_ERRONEA (hardcoded, no se puede cambiar).
    El motivo y observación son opcionales.
    """

    motivo_cierre: str | None = Field(
        default=None,
        max_length=500,
        description="Motivo por el cual la asignación fue errónea.",
    )

    observacion: str | None = Field(
        default=None,
        max_length=1000,
        description="Observación adicional.",
    )


class CambiarParticipacionIn(BaseSchema):
    """
    Payload para cambiar el tipo de participación de un período.

    Se usa en POST /periodos/{periodo_id}/cambiar-participacion.

    El nuevo tipo de participación es obligatorio y debe ser PRINCIPAL o ADJUNTA.
    El motivo es opcional y se registra en el cierre del período actual.
    """

    tipo_participacion: str = Field(
        ...,
        max_length=20,
        description="Nuevo tipo de participación: PRINCIPAL o ADJUNTA.",
    )

    motivo: str | None = Field(
        default=None,
        max_length=500,
        description="Motivo opcional del cambio de participación.",
    )


class CrearRespuestaBorradorIn(BaseSchema):
    """
    Payload para crear una respuesta en estado BORRADOR para un período.

    Se usa en POST /periodos/{periodo_id}/respuestas.

    El estado es siempre BORRADOR (hardcoded). No se permite emitir
    en este endpoint — eso se hace en la siguiente fase (5.3).
    """

    tipo_respuesta: str = Field(
        ...,
        max_length=20,
        description="Tipo de respuesta: INFORME, OBSERVACION, CONFORMIDAD, DESCARGO, OTRO.",
    )

    contenido: str | None = Field(
        default=None,
        max_length=5000,
        description="Contenido o texto de la respuesta.",
    )

    archivo: str | None = Field(
        default=None,
        max_length=500,
        description="Ruta/nombre del archivo adjunto (opcional).",
    )

    observacion: str | None = Field(
        default=None,
        max_length=1000,
        description="Observación adicional (opcional).",
    )
