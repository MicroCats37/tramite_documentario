"""
NotificacionAsignacion — Contexto de Asignación para una Notificacion.

Separa el contexto de asignación (SolicitudAsignacion) de la Notificacion core,
manteniendo la FK legacy en Notificacion para compatibilidad.
"""

from django.db import models

from core.models import BaseModel


class NotificacionAsignacion(BaseModel):
    """
    Contexto de Asignación (SolicitudAsignacion) asociado a una Notificacion.

    Una Notificacion puede estar vinculada a una SolicitudAsignacion que representa
    el área participante. Este modelo permite consultar notificaciones por contexto
    de asignación sin consultar la tabla Notificacion directamente.

    La relación con Notificacion es CASCADE: si se elimina la notificación,
    se elimina este contexto. La relación con SolicitudAsignacion también es
    CASCADE para mantener consistencia con el comportamiento legacy de
    Notificacion.asignacion (on_delete=CASCADE).
    """

    notificacion = models.ForeignKey(
        "notificaciones.Notificacion",
        on_delete=models.CASCADE,
        related_name="contexto_asignacion",
        verbose_name="Notificación",
    )
    asignacion = models.ForeignKey(
        "asignaciones.SolicitudAsignacion",
        on_delete=models.CASCADE,
        related_name="notificacion_contextos",
        verbose_name="Asignación",
    )

    class Meta:
        db_table = "asignaciones_notificacion_asignacion"
        verbose_name = "Contexto de Asignación de Notificación"
        verbose_name_plural = "Contextos de Asignación de Notificación"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["notificacion"],
                name="unique_notificacion_asignacion_context",
            ),
        ]

    def __str__(self):
        return f"Notificacion {self.notificacion_id} → Asignacion {self.asignacion_id}"
