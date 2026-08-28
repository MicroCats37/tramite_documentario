"""
AsignacionUsuario — User assignment to area and position with validity period.
"""

from django.db import models
from django.conf import settings

from core.models import BaseModel
from core_application.models import VigenciaModel


class AsignacionUsuario(VigenciaModel, BaseModel):
    """
    Assignment of a user to an area and position (cargo) with a validity period.
    Inherits from both VigenciaModel (periodo_inicio, periodo_fin) and BaseModel (id, created_at, updated_at).
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="asignaciones",
        verbose_name="Usuario",
    )

    area = models.ForeignKey(
        "Area",
        on_delete=models.PROTECT,
        related_name="asignaciones",
        verbose_name="Área",
    )

    cargo = models.ForeignKey(
        "Cargo",
        on_delete=models.PROTECT,
        related_name="asignaciones",
        verbose_name="Cargo",
    )

    class Meta:
        verbose_name = "Asignación de Usuario"
        verbose_name_plural = "Asignaciones de Usuarios"
        ordering = ["-periodo_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario"],
                condition=models.Q(periodo_fin__isnull=True),
                name="unique_active_assignment",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} → {self.area} / {self.cargo}"
