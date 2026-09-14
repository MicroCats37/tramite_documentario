"""
NotificacionSolicitud — Contexto de Solicitud para una Notificacion.

Este es el modelo consolidado de contexto para notificaciones relacionadas
con solicitudes. Reúne:
- Solicitud (requerida)
- Asignacion (opcional)
- Periodo (opcional)
- Conversacion (opcional, para menciones en comentarios)
- Mensaje (opcional, para menciones en comentarios)

La relación con Notificacion es CASCADE: si se elimina la notificación,
se elimina este contexto.
"""

from django.db import models

from core.models import BaseModel


class NotificacionSolicitud(BaseModel):
    """
    Contexto consolidado de Solicitud para una Notificacion.

    Este es el único modelo de contexto para notificaciones de dominio SOLICITUD.
    Agrupa solicitud (requerida), asignacion, periodo, conversacion y mensaje
    (todos opcionales).

    La relación con Notificacion es CASCADE.
    La relación con Solicitud es CASCADE.
    La relación con SolicitudAsignacion es SET_NULL: la asignación puede
        ser eliminada sin eliminar la notificación ni su contexto.
    La relación con SolicitudAsignacionPeriodo es SET_NULL: el período puede
        ser cerrado/eliminado sin eliminar la notificación ni su contexto.
    La relación con Conversacion es PROTECT: impide eliminar una conversación
        que tenga notificaciones asociadas (protege la integridad referencial).
    La relación con Mensaje es PROTECT: impide eliminar un mensaje que tenga
        notificaciones asociadas.
    """

    notificacion = models.ForeignKey(
        "notificaciones.Notificacion",
        on_delete=models.CASCADE,
        related_name="contexto_solicitud",
        verbose_name="Notificación",
    )
    solicitud = models.ForeignKey(
        "tramites.Solicitud",
        on_delete=models.CASCADE,
        related_name="notificacion_contextos",
        verbose_name="Solicitud",
    )
    asignacion = models.ForeignKey(
        "asignaciones.SolicitudAsignacion",
        on_delete=models.SET_NULL,
        related_name="notificacion_solicitud_contextos",
        verbose_name="Asignación",
        null=True,
        blank=True,
    )
    periodo = models.ForeignKey(
        "asignaciones.SolicitudAsignacionPeriodo",
        on_delete=models.SET_NULL,
        related_name="notificacion_contextos",
        verbose_name="Período",
        null=True,
        blank=True,
    )
    conversacion = models.ForeignKey(
        "conversaciones.Conversacion",
        on_delete=models.PROTECT,
        related_name="notificacion_contextos",
        verbose_name="Conversación",
        null=True,
        blank=True,
    )
    mensaje = models.ForeignKey(
        "conversaciones.Mensaje",
        on_delete=models.PROTECT,
        related_name="notificacion_contextos",
        verbose_name="Mensaje",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "asignaciones_notificacion_solicitud"
        verbose_name = "Contexto de Notificación"
        verbose_name_plural = "Contextos de Notificación"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["notificacion"],
                name="unique_notificacion_solicitud_context",
            ),
        ]

    def __str__(self):
        return f"Notificacion {self.notificacion_id} → Solicitud {self.solicitud_id}"
