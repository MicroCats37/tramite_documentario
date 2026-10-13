"""
SolicitudArchivo — Archivo adjunto a una solicitud (anexo).

Relacionado con Solicitud de forma similar a ExpedienteArchivo.
"""

from django.db import models

from core.models import BaseModel
from modules.usuarios.domain.models.usuario import Usuario

from .solicitud import Solicitud


class SolicitudArchivo(BaseModel):
    """
    Archivo adjunto a una solicitud (documento anexo).
    """

    solicitud = models.ForeignKey(
        Solicitud,
        on_delete=models.CASCADE,
        related_name="archivos",
        verbose_name="Solicitud",
    )
    archivo = models.FileField(
        max_length=1024,
        upload_to="tramites/solicitudes/",
        verbose_name="Archivo",
    )
    nombre_original = models.CharField(
        max_length=255,
        verbose_name="Nombre Original",
    )
    descripcion = models.TextField(
        null=True,
        blank=True,
        verbose_name="Descripción",
    )
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="archivos_solicitud_creados",
        verbose_name="Creado por",
    )

    class Meta:
        db_table = "tramites_solicitud_archivo"
        verbose_name = "Archivo de Solicitud"
        verbose_name_plural = "Archivos de Solicitud"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.nombre_original} — {self.solicitud}"
