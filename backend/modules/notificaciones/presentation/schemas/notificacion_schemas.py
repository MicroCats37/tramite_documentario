"""
Esquemas HTTP response para Notificacion — Schema Ninja para API.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from ninja import Field

from core.types import BaseSchema
from modules.notificaciones.domain.constants import AmbitoNotificacion, PrioridadNotificacion


class EstadoIndividual(str, Enum):
    """Estado individual de la notificación para el usuario actual."""

    NO_VISTA = "NO_VISTA"
    VISTA = "VISTA"
    ABIERTA = "ABIERTA"
    DESCARTADA = "DESCARTADA"


class NotificacionListItemOut(BaseSchema):
    """
    Item de notificación para la bandeja global (listado paginado).

    Contiene únicamente campos comunes a todas las notificaciones.
    Los campos contextuales (solicitud_id, expediente_id_publico, area_nombre,
    periodo_id, solicitud_asunto, periodo_ciclo, periodo_activo, participo,
    audiencia_tipo) se obtienen via GET /api/notificaciones/{id}/detalle.

    Contrato: 12 campos esenciales.
    """

    id: uuid.UUID = Field(..., description="ID único de la notificación")
    ambito: str = Field(..., description="Ámbito/discriminador: SOLICITUD, SISTEMA")
    evento: str = Field(..., description="Código de evento dentro del ámbito")
    prioridad: str = Field(..., description="Prioridad: NORMAL, ALTA, CRITICA")
    titulo: str = Field(..., description="Título")
    mensaje: Optional[str] = Field(None, description="Mensaje")
    ocurrido_en: datetime = Field(..., description="Fecha/hora en que ocurrió el evento")
    interactuada: bool = Field(..., description="¿El usuario ha interactuado con esta notificación?")
    vista: bool = Field(False, description="¿Fue vista?")
    abierta: bool = Field(False, description="¿Fue abierta?")
    descartada: bool = Field(False, description="¿Fue descartada?")
    estado_individual: EstadoIndividual = Field(..., description="Estado individual para el usuario actual")


# Schema con campos contextuales — usado internamente por el presenter para el detalle
# (se mantiene para referencia; detail endpoints usan NotificacionDetalleOut o NotificacionDetailOut)
class NotificacionItemOut(BaseSchema):
    """
    Item de notificación con contexto — DEPRECADO para listados.
    Use NotificacionListItemOut para GET /api/notificaciones/
    y NotificacionDetalleOut / NotificacionDetailOut para detalle.

    Este schema permanece para compatibilidad interna del presenter
    y backward compatibility donde aún se use.
    """

    id: uuid.UUID = Field(..., description="ID único de la notificación")
    ambito: str = Field(..., description="Ámbito/discriminador: SOLICITUD, SISTEMA")
    evento: str = Field(..., description="Código de evento dentro del ámbito")
    prioridad: str = Field(..., description="Prioridad: NORMAL, ALTA, CRITICA")
    titulo: str = Field(..., description="Título")
    mensaje: Optional[str] = Field(None, description="Mensaje")
    ocurrido_en: datetime = Field(..., description="Fecha/hora en que ocurrió el evento")
    solicitud_id: Optional[uuid.UUID] = Field(None, description="ID de la solicitud asociada")
    expediente_id_publico: Optional[str] = Field(None, description="ID público del expediente")
    area_nombre: Optional[str] = Field(None, description="Nombre del área")
    periodo_id: Optional[uuid.UUID] = Field(None, description="ID del período asociado")
    interactuada: bool = Field(..., description="¿El usuario ha interactuado con esta notificación?")
    vista: bool = Field(False, description="¿Fue vista?")
    abierta: bool = Field(False, description="¿Fue abierta?")
    descartada: bool = Field(False, description="¿Fue descartada?")

    # Campos adicionales
    audiencia_tipo: Optional[str] = Field(
        None,
        description="Tipo de audiencia calculado: AREA o USUARIO (basado en relaciones cargadas)",
    )
    estado_individual: EstadoIndividual = Field(..., description="Estado individual para el usuario actual")
    solicitud_asunto: Optional[str] = Field(None, description="Asunto del expediente de la solicitud")
    periodo_ciclo: Optional[int] = Field(None, description="Número de ciclo del período")
    periodo_activo: Optional[bool] = Field(None, description="Si el período está activo (abierto)")
    participo: Optional[bool] = Field(None, description="Si el usuario participó en el período")


class InteraccionOut(BaseSchema):
    """Interacción de un usuario con una notificación."""

    usuario_id: uuid.UUID = Field(..., description="ID del usuario")
    vista_at: Optional[datetime] = Field(None, description="Cuándo fue vista")
    abierta_at: Optional[datetime] = Field(None, description="Cuándo fue abierta")
    descartada_at: Optional[datetime] = Field(None, description="Cuándo fue descartada")


class NotificacionResumenOut(BaseSchema):
    """
    Resumen de contadores de notificaciones para el usuario autenticado.

    semantics:
    - total: todas las notificaciones del usuario (sin exclusión)
    - no_vistas: vista_at IS NULL AND abierta_at IS NULL AND descartada_at IS NULL
    - vistas: vista_at NOT NULL AND abierta_at IS NULL AND descartada_at IS NULL
    - abiertas: abierta_at NOT NULL AND descartada_at IS NULL
    - descartadas: descartada_at NOT NULL
    - sin_leer: alias de no_vistas (compatibilidad frontend, mismo valor)
    """

    total: int = Field(..., description="Total de notificaciones para el usuario")
    no_vistas: int = Field(..., description="Notificaciones no vistas (sin_interactuar)")
    vistas: int = Field(..., description="Notificaciones vistas pero no abiertas")
    abiertas: int = Field(..., description="Notificaciones abiertas")
    descartadas: int = Field(..., description="Notificaciones descartadas")
    sin_leer: int = Field(..., description="Alias de no_vistas para compatibilidad frontend")


class ExpedientePublicoOut(BaseSchema):
    """
    Datos públicos del expediente asociado a una notificación.

    Estructura anidada para el detalle contextual — no es un modelo Django.
    """

    id_publico: Optional[str] = Field(
        None,
        description="ID público del expediente (identificador visible para el usuario)",
    )
    asunto: Optional[str] = Field(
        None,
        description="Asunto del expediente",
    )


class PeriodoContextOut(BaseSchema):
    """
    Datos del período asociado a una notificación de SOLICITUD.

    Estructura anidada para el detalle contextual — no es un modelo Django.
    """

    id: Optional[uuid.UUID] = Field(
        None,
        description="ID del período",
    )
    numero_ciclo: Optional[int] = Field(
        None,
        description="Número de ciclo del período",
    )
    esta_abierto: Optional[bool] = Field(
        None,
        description="Si el período está actualmente abierto (activo)",
    )


class NotificacionDetalleOut(BaseSchema):
    """
    Detalle completo de una notificación con contexto restructurado.

    Presenta expediente y período como objetos anidados (expediente_publico, periodo)
    en lugar de campos planos.

    Para SOLICITUD: incluye contexto completo con expediente y período anidados.
    Para SISTEMA: expediente_publico y periodo son None.
    """

    id: uuid.UUID = Field(..., description="ID único de la notificación")
    ambito: str = Field(..., description="Ámbito/discriminador: SOLICITUD, SISTEMA")
    evento: str = Field(..., description="Código de evento dentro del ámbito")
    prioridad: str = Field(..., description="Prioridad: NORMAL, ALTA, CRITICA")
    titulo: str = Field(..., description="Título")
    mensaje: Optional[str] = Field(None, description="Mensaje")
    ocurrido_en: datetime = Field(..., description="Fecha/hora en que ocurrió el evento")
    interactuada: bool = Field(..., description="¿El usuario ha interactuado con esta notificación?")
    vista: bool = Field(False, description="¿Fue vista?")
    abierta: bool = Field(False, description="¿Fue abierta?")
    descartada: bool = Field(False, description="¿Fue descartada?")
    estado_individual: EstadoIndividual = Field(..., description="Estado individual para el usuario actual")
    audiencia_tipo: Optional[str] = Field(
        None,
        description="Tipo de audiencia: AREA o USUARIO",
    )
    generada_por_nombres: Optional[str] = Field(
        None,
        description="Nombre completo del usuario que generó la notificación",
    )

    # Contexto SOLICITUD
    solicitud_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de la solicitud asociada",
    )
    expediente_publico: Optional[ExpedientePublicoOut] = Field(
        None,
        description="Datos públicos del expediente (anidado)",
    )
    area_id: Optional[uuid.UUID] = Field(
        None,
        description="ID del área",
    )
    area_nombre: Optional[str] = Field(
        None,
        description="Nombre del área",
    )
    periodo: Optional[PeriodoContextOut] = Field(
        None,
        description="Datos del período (anidado)",
    )
    interacciones: list[InteraccionOut] = Field(
        default_factory=list,
        description="Interacciones del usuario actual con la notificación",
    )
    participo: Optional[bool] = Field(
        None,
        description="Si el usuario participó en el período/notificación",
    )
    solicitud_asunto: Optional[str] = Field(
        None,
        description="Asunto de la solicitud (para referencia rápida)",
    )


# Schema plano original — backward compatible con endpoint existente GET /notificaciones/{id}
# NO se modifica para no romper consumidores existentes (migrados al nuevo /detalle en batch 3)
class NotificacionDetailOut(BaseSchema):
    """
    Detalle completo de una notificación (schema plano original).

    Este schema se mantiene sin cambios para backward compatibility.
    Los nuevos consumidores deben usar NotificacionDetalleOut (schema restructurado).
    """

    id: uuid.UUID = Field(..., description="ID único de la notificación")
    ambito: str = Field(..., description="Ámbito/discriminador: SOLICITUD, SISTEMA")
    evento: str = Field(..., description="Código de evento dentro del ámbito")
    prioridad: str = Field(..., description="Prioridad: NORMAL, ALTA, CRITICA")
    titulo: str = Field(..., description="Título")
    mensaje: Optional[str] = Field(None, description="Mensaje")
    ocurrido_en: datetime = Field(..., description="Fecha/hora en que ocurrió el evento")
    generada_por_nombres: Optional[str] = Field(None, description="Quién generó la notificación")

    # Contexto
    area_id: Optional[uuid.UUID] = Field(None, description="ID del área")
    area_nombre: Optional[str] = Field(None, description="Nombre del área")
    solicitud_id: Optional[uuid.UUID] = Field(None, description="ID de la solicitud")
    expediente_id_publico: Optional[str] = Field(None, description="ID público del expediente")
    expediente_asunto: Optional[str] = Field(None, description="Asunto del expediente")
    periodo_id: Optional[uuid.UUID] = Field(None, description="ID del período")

    # Interacciones del actor actual
    interacciones: list[InteraccionOut] = Field(default_factory=list, description="Interacciones del usuario")

    # Campos adicionales
    audiencia_tipo: Optional[str] = Field(
        None,
        description="Tipo de audiencia calculado: AREA o USUARIO (basado en relaciones cargadas)",
    )
    estado_individual: EstadoIndividual = Field(..., description="Estado individual para el usuario actual")
    solicitud_asunto: Optional[str] = Field(None, description="Asunto del expediente de la solicitud")
    periodo_ciclo: Optional[int] = Field(None, description="Número de ciclo del período")
    periodo_activo: Optional[bool] = Field(None, description="Si el período está activo (abierto)")
    participo: Optional[bool] = Field(None, description="Si el usuario participó en el período")
