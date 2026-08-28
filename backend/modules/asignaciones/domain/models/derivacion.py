"""
SolicitudDerivacion — Movimiento formal entre períodos de asignación.

Representa la derivación o devolución de un período a otro.
"""

from django.db import models

from core.models import BaseModel
from modules.usuarios.domain.models import Usuario

from ..constants import TipoDerivacion


class SolicitudDerivacion(BaseModel):
    """
    Movimiento formal de un período hacia otro.

    Ejemplo: Arquitectura/Ciclo 1 es derivada a Estructuras/Ciclo 1.
    Luego Estructuras la devuelve a Arquitectura/Ciclo 2.
    """

    periodo_origen = models.ForeignKey(
        "asignaciones.SolicitudAsignacionPeriodo",
        on_delete=models.CASCADE,
        related_name="derivaciones_enviadas",
        verbose_name="Período de Origen",
    )
    periodo_destino = models.ForeignKey(
        "asignaciones.SolicitudAsignacionPeriodo",
        on_delete=models.CASCADE,
        related_name="derivaciones_recibidas",
        verbose_name="Período de Destino",
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoDerivacion.choices,
        default=TipoDerivacion.DERIVACION,
        verbose_name="Tipo",
        help_text="DERIVACION o DEVOLUCION.",
    )
    derivado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="derivaciones_realizadas",
        verbose_name="Derivado por",
    )
    fecha_derivacion = models.DateTimeField(
        verbose_name="Fecha de Derivación",
        help_text="Fecha real del movimiento.",
    )
    motivo = models.TextField(
        verbose_name="Motivo",
        help_text="Razón de la derivación.",
    )
    observacion = models.TextField(
        null=True,
        blank=True,
        verbose_name="Observación",
        help_text="Información complementaria.",
    )

    class Meta:
        db_table = "asignaciones_solicitud_derivacion"
        verbose_name = "Derivación de Solicitud"
        verbose_name_plural = "Derivaciones de Solicitud"
        ordering = ["-fecha_derivacion"]

    def __str__(self):
        return f"{self.periodo_origen} → {self.periodo_destino} ({self.tipo})"
