"""
SolicitudAsignacionPeriodo y SolicitudAsignacionUsuario — Períodos operativos y usuarios participantes.

SolicitudAsignacionPeriodo representa cada entrada/reingreso operativo del área.
SolicitudAsignacionUsuario representa los usuarios que trabajan por el área durante un período.
"""

from django.db import models

from core.models import BaseModel
from modules.usuarios.domain.models import Usuario

from ..constants import EstadoPeriodo, TipoCierre, TipoParticipacion


class SolicitudAsignacionPeriodoManager(models.Manager):
    """Manager that returns only open periods."""

    def abiertos(self):
        return self.get_queryset().filter(fecha_fin__isnull=True)

    def cerrados(self):
        return self.get_queryset().filter(fecha_fin__isnull=False)


class SolicitudAsignacionPeriodo(BaseModel):
    """
    Cada entrada/reingreso operativo del área a una solicitud.

    Ejemplo: Arquitectura entra, es derivada a Estructuras, y luego
    Arquitectura reingresa en un segundo período.
    """

    asignacion = models.ForeignKey(
        "asignaciones.SolicitudAsignacion",
        on_delete=models.CASCADE,
        related_name="periodos",
        verbose_name="Asignación",
    )
    numero_ciclo = models.PositiveIntegerField(
        verbose_name="Número de Ciclo",
        help_text="Número secuencial del ingreso del área: 1, 2, 3...",
    )
    tipo_participacion = models.CharField(
        max_length=20,
        choices=TipoParticipacion.choices,
        default=TipoParticipacion.PRINCIPAL,
        verbose_name="Tipo de Participación",
        help_text="PRINCIPAL o ADJUNTA para este ciclo.",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoPeriodo.choices,
        default=EstadoPeriodo.PENDIENTE,
        verbose_name="Estado",
    )
    fecha_inicio = models.DateTimeField(
        verbose_name="Fecha de Inicio",
        help_text="Fecha real en que comienza este período.",
    )
    fecha_fin = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Fin",
        help_text="Fecha real de cierre. NULL mientras siga abierto.",
    )
    tipo_cierre = models.CharField(
        max_length=20,
        choices=TipoCierre.choices,
        null=True,
        blank=True,
        verbose_name="Tipo de Cierre",
        help_text="FINALIZADO, DERIVADO, RETIRADO, RECHAZADO, ANULADO.",
    )
    iniciado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="periodos_iniciados",
        verbose_name="Iniciado por",
        null=True,
        blank=True,
    )
    finalizado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="periodos_finalizados",
        verbose_name="Finalizado por",
        null=True,
        blank=True,
    )
    motivo_cierre = models.TextField(
        null=True,
        blank=True,
        verbose_name="Motivo de Cierre",
    )
    observacion = models.TextField(
        null=True,
        blank=True,
        verbose_name="Observación",
        help_text="Información particular de ese ciclo.",
    )

    objects = models.Manager()
    abiertos = SolicitudAsignacionPeriodoManager()

    class Meta:
        db_table = "asignaciones_solicitud_asignacion_periodo"
        verbose_name = "Período de Asignación"
        verbose_name_plural = "Períodos de Asignación"
        ordering = ["asignacion", "numero_ciclo"]
        constraints = [
            models.UniqueConstraint(
                fields=["asignacion", "numero_ciclo"],
                name="unique_asignacion_numero_ciclo",
            ),
            # Un único período abierto por asignación
            models.UniqueConstraint(
                fields=["asignacion"],
                condition=models.Q(fecha_fin__isnull=True),
                name="unique_asignacion_periodo_abierto",
            ),
        ]

    def __str__(self):
        return f"{self.asignacion} — Ciclo {self.numero_ciclo}"

    @property
    def esta_abierto(self):
        """True if this period is still open."""
        return self.fecha_fin is None


class SolicitudAsignacionUsuario(BaseModel):
    """
    Usuarios que trabajan por el área durante un período determinado.

    Ejemplo: Arquitectura/Ciclo 2 tiene a Juan (responsable),
    Pedro (colaborador) y María (revisor).
    """

    periodo = models.ForeignKey(
        SolicitudAsignacionPeriodo,
        on_delete=models.CASCADE,
        related_name="usuarios",
        verbose_name="Período",
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="asignaciones_periodo",
        verbose_name="Usuario",
    )
    rol = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Rol",
        help_text="Responsable, colaborador, revisor, etc.",
    )
    fecha_inicio = models.DateTimeField(
        verbose_name="Fecha de Inicio",
        help_text="Fecha real en que comenzó su participación.",
    )
    fecha_fin = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Fin",
        help_text="NULL mientras continúe participando.",
    )
    asignado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="asignaciones_usuarios",
        verbose_name="Asignado por",
        null=True,
        blank=True,
        help_text="Usuario que incorporó. Puede ser él mismo si se autoasigna.",
    )
    retirado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="retiros_usuarios",
        verbose_name="Retirado por",
        null=True,
        blank=True,
    )
    motivo_retiro = models.TextField(
        null=True,
        blank=True,
        verbose_name="Motivo de Retiro",
    )

    class Meta:
        db_table = "asignaciones_solicitud_asignacion_usuario"
        verbose_name = "Usuario de Asignación"
        verbose_name_plural = "Usuarios de Asignación"
        ordering = ["periodo", "fecha_inicio"]
        constraints = [
            # Un único participante activo por período
            models.UniqueConstraint(
                fields=["periodo", "usuario"],
                condition=models.Q(fecha_fin__isnull=True),
                name="unique_periodo_usuario_activo",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} en {self.periodo}"

    @property
    def esta_activo(self):
        """True if this user participation is still active."""
        return self.fecha_fin is None
