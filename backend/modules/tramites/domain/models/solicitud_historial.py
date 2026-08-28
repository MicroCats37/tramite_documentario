"""
SolicitudEstadoHistorial — Registro de auditoría inmutable de cambios de estado.

Cada transición de estado de la solicitud genera un registro en esta tabla.
Es append-only: no debe modificarse ni eliminarse una vez creado.
"""

from django.db import models

from core.models import BaseModel
from modules.usuarios.domain.models.usuario import Usuario

from ..constants import EstadoCambio
from .solicitud import Solicitud


class OrigenCambio(models.TextChoices):
    """Origen/motivo del cambio de estado de la solicitud."""

    CREACION = "CREACION", "Creación"
    CAMBIO_ESTADO = "CAMBIO_ESTADO", "Cambio de Estado"
    CIERRE = "CIERRE", "Cierre"
    ANULACION = "ANULACION", "Anulación"


class SolicitudEstadoHistorial(BaseModel):
    """
    Historial de cambios de estado de una solicitud.

    Registra el estado anterior, el nuevo estado, quién lo realizó,
    y opcionalmente el motivo y una observación.
    """

    solicitud = models.ForeignKey(
        Solicitud,
        on_delete=models.CASCADE,
        related_name="historial_estados",
        verbose_name="Solicitud",
    )
    estado_anterior = models.CharField(
        max_length=30,
        choices=EstadoCambio.choices,
        null=True,
        blank=True,
        verbose_name="Estado Anterior",
    )
    estado_nuevo = models.CharField(
        max_length=30,
        choices=EstadoCambio.choices,
        verbose_name="Estado Nuevo",
    )
    fecha_cambio = models.DateTimeField(
        default=None,
        null=True,
        blank=True,
        verbose_name="Fecha del Cambio",
        help_text="Fecha real del cambio. No usa auto_now_add para permitir fechas históricas.",
    )
    cambiado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="cambios_estado_solicitud",
        verbose_name="Cambiado por",
    )
    motivo = models.TextField(
        null=True,
        blank=True,
        verbose_name="Motivo",
    )
    observacion = models.TextField(
        null=True,
        blank=True,
        verbose_name="Observación",
    )
    origen = models.CharField(
        max_length=30,
        choices=OrigenCambio.choices,
        null=True,
        blank=True,
        verbose_name="Origen",
        help_text="Qué acción o evento disparó el cambio de estado.",
    )

    class Meta:
        db_table = "tramites_solicitud_estado_historial"
        verbose_name = "Historial de Estado de Solicitud"
        verbose_name_plural = "Historiales de Estado de Solicitud"
        ordering = ["fecha_cambio"]

    def __str__(self):
        return f"{self.solicitud} — {self.estado_anterior} → {self.estado_nuevo}"
