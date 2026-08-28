"""
ExpedienteAntecedente — Tabla explícita para vincular un trámite nuevo con uno histórico.

Actúa como tabla intermedia (through) entre Expediente y sí mismo,
representando la relación de antecedencia sin usar M2M mágicos de Django.
"""

from django.db import models

from core.models import BaseModel

from .expediente import Expediente


class ExpedienteAntecedente(BaseModel):
    """
    Relación explícita entre un expediente nuevo y uno antecedentado (histórico).

    La unicidad se garantiza a nivel de base de datos mediante constraint.
    No posee campo `creado_por` ya que es implícito al expediente principal.
    """

    expediente = models.ForeignKey(
        Expediente,
        on_delete=models.CASCADE,
        related_name="antecedentes_vinculados",
        verbose_name="Expediente (Nuevo)",
        help_text="Trámite nuevo que tiene este antecedente.",
    )
    antecedente = models.ForeignKey(
        Expediente,
        on_delete=models.CASCADE,
        related_name="antecedentes_de",
        verbose_name="Antecedente",
        help_text="Trámite histórico vinculado como antecedente.",
    )
    categoria = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Categoría",
        help_text="Clasificación del vínculo (ej: subsanación, recurso, etc).",
    )
    observaciones = models.TextField(
        null=True,
        blank=True,
        verbose_name="Observaciones",
    )

    class Meta:
        db_table = "tramites_expediente_antecedente"
        verbose_name = "Antecedente de Expediente"
        verbose_name_plural = "Antecedentes de Expediente"
        constraints = [
            models.UniqueConstraint(
                fields=["expediente", "antecedente"],
                name="unique_expediente_antecedente",
            ),
        ]

    def __str__(self):
        return f"Exp {self.expediente.id_publico} ← Antecedente {self.antecedente.id_publico}"
