"""
Cargo — Job position/role model.
"""

from django.db import models

from core.models import BaseModel


class Cargo(BaseModel):
    """
    Job position or role within the organization.
    """

    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre del Cargo",
    )

    activo = models.BooleanField(
        default=True,
        verbose_name="¿Está Activo?",
    )

    class Meta:
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
