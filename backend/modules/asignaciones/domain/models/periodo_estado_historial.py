"""
SolicitudAsignacionPeriodoEstadoHistorial — Historial de estados operativos del período.

Cada transición de estado operativo del período se registra aquí para auditoría
y métricas de tiempo por estado.

El estado operativo es independiente de participantes y respuestas.
Modelo recomendado: PENDIENTE → EN_GESTION → CERRADO.
"""

from django.db import models

from core.models import BaseModel
from modules.usuarios.domain.models import Usuario

from ..constants import EstadoPeriodoOperativo, OrigenEstadoPeriodo


class SolicitudAsignacionPeriodoEstadoHistorial(BaseModel):
    """
    Historial de transiciones de estado operativo del período.

    Cada registro representa un cambio de estado con actor, fecha y origen.
    El primer registro de un período es la creación (estado_anterior = NULL).
    """

    periodo = models.ForeignKey(
        "asignaciones.SolicitudAsignacionPeriodo",
        on_delete=models.CASCADE,
        related_name="historial_estados",
        verbose_name="Período",
    )
    estado_anterior = models.CharField(
        max_length=20,
        choices=EstadoPeriodoOperativo.choices,
        null=True,
        blank=True,
        verbose_name="Estado Anterior",
        help_text="Estado previo. NULL para el primer registro (creación).",
    )
    estado_nuevo = models.CharField(
        max_length=20,
        choices=EstadoPeriodoOperativo.choices,
        verbose_name="Estado Nuevo",
    )
    fecha_cambio = models.DateTimeField(
        verbose_name="Fecha del Cambio",
        help_text="Fecha real del cambio. No es auto_now_add para permitir fechas históricas.",
    )
    cambiado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="cambios_estado_periodo",
        verbose_name="Cambiado por",
        null=True,
        blank=True,
        help_text="Usuario que ejecutó la transición. Nullable para sistema/Legacy.",
    )
    motivo = models.TextField(
        null=True,
        blank=True,
        verbose_name="Motivo",
        help_text="Razón opcional del cambio.",
    )
    origen = models.CharField(
        max_length=30,
        choices=OrigenEstadoPeriodo.choices,
        null=True,
        blank=True,
        verbose_name="Origen",
        help_text="Qué acción o evento disparó el cambio.",
    )

    class Meta:
        db_table = "asignaciones_periodo_estado_historial"
        verbose_name = "Historial de Estado de Período"
        verbose_name_plural = "Historiales de Estado de Período"
        ordering = ["periodo", "fecha_cambio"]
        indexes = [
            models.Index(fields=["periodo", "fecha_cambio"]),
            models.Index(fields=["estado_nuevo"]),
        ]

    def __str__(self):
        return f"{self.periodo} — {self.estado_anterior or '∅'} → {self.estado_nuevo}"
