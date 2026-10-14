"""
TipoDocumento — catálogo de tipos de documento que pueden presentar los ciudadanos.

Cada tipo tiene un nombre (código) y una descripción legible.
Ejemplos: OFICIO ("Oficio"), SOLICITUD ("Solicitud"), CARTA ("Carta").
"""
from django.db import models

from core.models import BaseModel


class TipoDocumento(BaseModel):
    """
    Catálogo de tipos de documento que pueden asociarse a un Expediente.

    Es un registro de referencia. Cada Expediente apunta a un TipoDocumento
    via ForeignKey.

    El campo `nombre` usa los códigos existentes de la enumeración original
    (OFICIO, CARTA, SOLICITUD, etc.) para mantener compatibilidad hacia atrás
    con payloads que ya usan esos códigos como string.
    """

    nombre = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Nombre (código)",
        help_text="Código único, ej. OFICIO, CARTA, SOLICITUD",
    )
    descripcion = models.CharField(
        max_length=100,
        verbose_name="Descripción",
        help_text="Descripción legible, ej. 'Oficio', 'Carta', 'Solicitud'",
    )

    class Meta:
        db_table = "tramites_tipo_documento"
        verbose_name = "Tipo de Documento"
        verbose_name_plural = "Tipos de Documento"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} — {self.descripcion}"
