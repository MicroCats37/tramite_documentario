"""
NotificacionPeriodo — Contexto de Período para una Notificacion.

Separa el contexto de período (SolicitudAsignacionPeriodo) de la Notificacion core,
manteniendo la FK legacy en Notificacion para compatibilidad.
"""

from django.db import models

from core.models import BaseModel


class NotificacionPeriodo(BaseModel):
    """
    Contexto de Período (SolicitudAsignacionPeriodo) asociado a una Notificacion.

    Una Notificacion puede estar vinculada a un Período específico. Este modelo
    permite consultar notificaciones por contexto de período sin consultar la
    tabla Notificacion directamente.

    La relación con Notificacion es CASCADE: si se elimina la notificación,
    se elimina este contexto. La relación con SolicitudAsignacionPeriodo es
    SET_NULL: el período puede ser cerrado/eliminado sin eliminar la notificación
    ni su contexto, manteniendo consistencia con el comportamiento establecido
    en NotificacionSolicitud.periodo (on_delete=SET_NULL).
    """

    notificacion = models.ForeignKey(
        "notificaciones.Notificacion",
        on_delete=models.CASCADE,
        related_name="contexto_periodo",
        verbose_name="Notificación",
    )
    periodo = models.ForeignKey(
        "asignaciones.SolicitudAsignacionPeriodo",
        on_delete=models.SET_NULL,
        related_name="notificacion_periodo_contextos",
        verbose_name="Período",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "asignaciones_notificacion_periodo"
        verbose_name = "Contexto de Período de Notificación"
        verbose_name_plural = "Contextos de Período de Notificación"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["notificacion"],
                name="unique_notificacion_periodo_context",
            ),
        ]

    def __str__(self):
        return f"Notificacion {self.notificacion_id} → Periodo {self.periodo_id}"
