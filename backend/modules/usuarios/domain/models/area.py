"""
Area — Organizational area/department model.
"""

from django.db import models
from django.utils.text import slugify

from core.models import BaseModel


class Area(BaseModel):
    """
    Organizational area or department.
    """

    nombre = models.CharField(
        max_length=120,
        unique=True,
        verbose_name="Nombre del Área",
    )

    descripcion = models.TextField(
        null=True,
        blank=True,
        verbose_name="Descripción",
    )

    activo = models.BooleanField(
        default=True,
        verbose_name="¿Está Activo?",
    )

    class Meta:
        verbose_name = "Área"
        verbose_name_plural = "Áreas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def slug(self):
        return slugify(self.nombre)
