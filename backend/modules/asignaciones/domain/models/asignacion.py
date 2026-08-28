"""
SolicitudAsignacion — Relación estable entre una Solicitud y un Área.

Representa las áreas que participan o participaron en una solicitud.
Restricción UNIQUE(solicitud, area).
"""

from django.db import models

from core.models import BaseModel
from modules.usuarios.domain.models import Area


class SolicitudAsignacion(BaseModel):
    """
    Relación entre una Solicitud y un Área participante.

    Responde: ¿Qué áreas participan o participaron en esta solicitud?
    Una única SolicitudAsignacion por área dentro de una misma solicitud.
    """

    solicitud = models.ForeignKey(
        "tramites.Solicitud",
        on_delete=models.CASCADE,
        related_name="asignaciones",
        verbose_name="Solicitud",
    )
    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name="solicitud_asignaciones",
        verbose_name="Área",
    )
    bloquea_cierre = models.BooleanField(
        default=False,
        verbose_name="¿Bloquea el Cierre?",
        help_text=(
            "Si debe quedar resuelta para cerrar la solicitud. "
            "NOTA: La regla global de cierre está DIFERIDA — este campo no se usa "
            "actualmente en la lógica de negocio. Se mantiene por compatibilidad."
        ),
    )
    fecha_incorporacion = models.DateTimeField(
        verbose_name="Fecha de Incorporación",
        help_text="Fecha real en que el área fue incorporada al trámite.",
    )
    incorporado_por = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
        related_name="incorporaciones",
        verbose_name="Incorporado por",
        null=True,
        blank=True,
    )
    observacion = models.TextField(
        null=True,
        blank=True,
        verbose_name="Observación",
        help_text="Información general de la relación Solicitud–Área.",
    )

    class Meta:
        db_table = "asignaciones_solicitud_asignacion"
        verbose_name = "Asignación de Solicitud"
        verbose_name_plural = "Asignaciones de Solicitud"
        ordering = ["-fecha_incorporacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["solicitud", "area"],
                name="unique_solicitud_area",
            ),
        ]

    def __str__(self):
        return f"{self.solicitud} — {self.area}"
