"""
Conversacion — Hilo de comunicación entre participantes.
"""

from django.db import models

from core.models import BaseModel
from modules.usuarios.domain.models.usuario import Usuario


class Conversacion(BaseModel):
    """
    Hilo de comunicación que agrupa mensajes entre participantes.

    Puede estar asociada a una Solicitud vía el puente SolicitudConversacion.
    No sabe de áreas ni de participantes directamente — esas lógicas
    pertenecen al módulo consumidor (ej. asignaciones).
    """

    titulo = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Título",
        help_text="Título opcional de la conversación.",
    )
    creada_por = models.ForeignKey(
        Usuario,
        related_name="conversaciones_creadas",
        on_delete=models.PROTECT,
        verbose_name="Creada por",
    )
    fecha_inicio = models.DateTimeField(
        verbose_name="Fecha de inicio",
    )
    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de cierre",
    )
    cerrado_por = models.ForeignKey(
        Usuario,
        null=True,
        blank=True,
        related_name="conversaciones_cerradas",
        on_delete=models.PROTECT,
        verbose_name="Cerrada por",
    )

    class Meta:
        db_table = "conversaciones_conversacion"
        verbose_name = "Conversación"
        verbose_name_plural = "Conversaciones"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return f"Conversación {self.id} — {self.titulo or 'Sin título'}"
