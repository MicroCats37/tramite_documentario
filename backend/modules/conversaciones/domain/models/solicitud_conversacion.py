"""
Puente entre Solicitud y Conversación.

Este modelo vive en el módulo conversaciones para mantener el núcleo
de mensajería desacoplado. La relación inversa está en tramites.Solicitud.
"""

from django.db import models

from core.models import BaseModel


class SolicitudConversacion(BaseModel):
    """
    Asocia una conversación a una solicitud.

    Una Solicitud tiene una única Conversación activa y viceversa.
    """

    solicitud = models.OneToOneField(
        "tramites.Solicitud",
        related_name="conversacionpuente",
        on_delete=models.CASCADE,
        verbose_name="Solicitud",
    )
    conversacion = models.OneToOneField(
        "Conversacion",
        related_name="solicitudpuente",
        on_delete=models.CASCADE,
        verbose_name="Conversación",
    )

    class Meta:
        db_table = "conversaciones_solicitud_conversacion"
        verbose_name = "Puente Solicitud-Conversación"
        verbose_name_plural = "Puentes Solicitud-Conversación"
        constraints = [
            models.UniqueConstraint(
                fields=["solicitud"],
                name="unique_solicitud_conversacion",
            ),
            models.UniqueConstraint(
                fields=["conversacion"],
                name="unique_conversacion_solicitud",
            ),
        ]

    def __str__(self):
        return f"SolicitudConversación: {self.solicitud_id} ↔ {self.conversacion_id}"
