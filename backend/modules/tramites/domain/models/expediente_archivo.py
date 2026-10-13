"""
ExpedienteArchivo — Tabla 1:N que unifica el documento principal y los anexos.

Evita contaminar el modelo Expediente con campos de archivos.
"""

from django.db import models

from core.models import BaseModel
from modules.usuarios.domain.models.usuario import Usuario

from ..constants import TipoArchivo
from .expediente import Expediente


class ExpedienteArchivo(BaseModel):
    """
    Archivo adjunto a un expediente (documento principal o anexo).

    Utiliza `tipo_archivo` (PRINCIPAL / ANEXO) en lugar de booleanos
    para clasificar el archivo.

    Constraint: un único archivo PRINCIPAL por expediente.
    """

    expediente = models.ForeignKey(
        Expediente,
        on_delete=models.CASCADE,
        related_name="archivos",
        verbose_name="Expediente",
    )
    tipo_archivo = models.CharField(
        max_length=20,
        choices=TipoArchivo.choices,
        verbose_name="Tipo de Archivo",
    )
    archivo = models.FileField(
        max_length=1024,
        upload_to="tramites/expedientes/",
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
        related_name="archivos_expediente_creados",
        verbose_name="Creado por",
    )

    class Meta:
        db_table = "tramites_expediente_archivo"
        verbose_name = "Archivo de Expediente"
        verbose_name_plural = "Archivos de Expediente"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["expediente"],
                condition=models.Q(tipo_archivo=TipoArchivo.PRINCIPAL),
                name="unique_expediente_principal_archivo",
            ),
        ]

    def __str__(self):
        return f"{self.tipo_archivo} — {self.nombre_original}"
