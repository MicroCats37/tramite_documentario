"""
Solicitud — Contenedor del estado global del trámite en la institución.

Representa la instancia de trámite abierta a partir de un expediente.
No contiene `area_responsable` ni `usuario_asignado` — esos van en el
módulo de asignaciones.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from modules.usuarios.domain.models.usuario import Usuario

from ..constants import EstadoSolicitud, Prioridad
from .expediente import Expediente


class Solicitud(BaseModel):
    """
    Modelo que representa una solicitud/trámite en curso.

    Contiene el estado global de la gestión del trámite y sus fechas
    críticas para medición de plazos. Se crea junto con el expediente
    asociado mediante relación OneToOne.
    """

    expediente = models.OneToOneField(
        Expediente,
        on_delete=models.CASCADE,
        related_name="solicitud",
        verbose_name="Expediente",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoSolicitud.choices,
        default=EstadoSolicitud.REGISTRADA,
        verbose_name="Estado",
    )
    prioridad = models.CharField(
        max_length=20,
        choices=Prioridad.choices,
        default=Prioridad.MEDIA,
        verbose_name="Prioridad",
    )
    fecha_registro = models.DateTimeField(
        verbose_name="Fecha de Registro",
        help_text="Fecha en que se creó la solicitud.",
    )
    fecha_inicio_gestion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Inicio de Gestión",
        help_text="Fecha en que se empieza a gestionar. Mide tiempos muertos.",
    )
    fecha_limite = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha Límite",
    )
    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Cierre",
    )
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="solicitudes_creadas",
        verbose_name="Creado por",
    )
    observacion = models.TextField(
        null=True,
        blank=True,
        verbose_name="Observación",
    )

    history = HistoricalRecords()

    class Meta:
        db_table = "tramites_solicitud"
        verbose_name = "Solicitud"
        verbose_name_plural = "Solicitudes"
        ordering = ["-fecha_registro"]

    def __str__(self):
        return f"Solicitud {self.expediente.id_publico} — {self.estado}"
