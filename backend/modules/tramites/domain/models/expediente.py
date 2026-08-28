"""
Expediente — Representa la data fría del ciudadano y el documento ingresado.

Es inmutable a nivel de flujo. El número es auto-incremental y se reinicia cada año.
No posee archivos adjuntos en la misma tabla ni M2M mágicos para antecedentes.
La auditoría de cambios se realiza con django-simple-history.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from modules.usuarios.domain.models.usuario import Usuario

from ..constants import TipoDocumento, TipoPersona


class Expediente(BaseModel):
    """
    Modelo principal que representa un expediente/trámite ingresado.

    Contiene los datos del ciudadano (razón social, nombres, apellidos, contacto)
    y los datos del documento ingresado (tipo, número, folios, asunto).
    El número de expediente es auto-incremental por año.

    No debe contener lógica de negocio — solo campos, Meta y métodos de
    conveniencia triviales.
    """

    numero = models.PositiveIntegerField(
        verbose_name="Número de Expediente",
        help_text="Número auto-incremental, se reinicia cada año.",
    )
    tipo_persona = models.CharField(
        max_length=20,
        choices=TipoPersona.choices,
        verbose_name="Tipo de Persona",
    )
    dni = models.CharField(
        max_length=8,
        null=True,
        blank=True,
        verbose_name="DNI",
    )
    ruc = models.CharField(
        max_length=11,
        null=True,
        blank=True,
        verbose_name="RUC",
    )
    cip = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="CIP",
    )
    razon_social = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Razón Social",
    )
    nombres = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name="Nombres",
    )
    apellidos = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name="Apellidos",
    )
    correo = models.EmailField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Correo Electrónico",
    )
    telefono = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Teléfono",
    )
    tipo_documento = models.CharField(
        max_length=20,
        choices=TipoDocumento.choices,
        verbose_name="Tipo de Documento",
    )
    numero_documento = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Número de Documento",
    )
    numero_folios = models.PositiveIntegerField(
        default=0,
        verbose_name="Número de Folios",
    )
    asunto = models.TextField(
        verbose_name="Asunto",
    )
    observaciones = models.TextField(
        null=True,
        blank=True,
        verbose_name="Observaciones",
    )
    fecha_registro = models.DateTimeField(
        verbose_name="Fecha de Registro",
        help_text="Fecha real de ingreso del trámite al sistema.",
    )
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="expedientes_creados",
        verbose_name="Creado por",
    )

    history = HistoricalRecords()

    class Meta:
        db_table = "tramites_expediente"
        verbose_name = "Expediente"
        verbose_name_plural = "Expedientes"
        ordering = ["-fecha_registro", "-numero"]

    def __str__(self):
        return f"{self.id_publico} — {self.asunto[:50]}"

    @property
    def id_publico(self) -> str:
        """
        Identificador público del expediente con formato LIMA-{año}-{número:04d}.

        Ejemplo: LIMA-2026-0001
        """
        year = self.fecha_registro.year if self.fecha_registro else "----"
        return f"LIMA-{year}-{self.numero:04d}"
