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
    # Direct FK to central Archivo model — replaces legacy FileField.
    archivo = models.ForeignKey(
        "tramites.Archivo",
        on_delete=models.PROTECT,
        related_name="expediente_archivos",
        null=True,
        blank=True,
        verbose_name="Archivo",
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
        nombre = self.archivo.nombre_original if self.archivo else "Sin archivo"
        return f"{self.tipo_archivo} — {nombre}"
