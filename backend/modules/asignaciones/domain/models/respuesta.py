"""
SolicitudAsignacionRespuesta — Respuesta formal del área.

La respuesta formal pertenece al área (período), no al usuario individual.
"""

from django.db import models

from core.models import BaseModel
from modules.usuarios.domain.models import Usuario

from ..constants import EstadoRespuesta, TipoRespuesta


class SolicitudAsignacionRespuesta(BaseModel):
    """
    Respuesta formal del área a una solicitud.

    No es la respuesta personal del usuario — es institucionalmente
    del área. Ejemplo: Área Arquitectura responde con emitido_por=María,
    pero la respuesta pertenece a Arquitectura/Ciclo 2.
    """

    periodo = models.ForeignKey(
        "asignaciones.SolicitudAsignacionPeriodo",
        on_delete=models.CASCADE,
        related_name="respuestas",
        verbose_name="Período",
        help_text="Período que produjo la respuesta.",
    )
    tipo_respuesta = models.CharField(
        max_length=20,
        choices=TipoRespuesta.choices,
        verbose_name="Tipo de Respuesta",
        help_text="Informe, observación, conformidad, etc.",
    )
    contenido = models.TextField(
        null=True,
        blank=True,
        verbose_name="Contenido",
        help_text="Texto de respuesta.",
    )
    # Nullable FK to central Archivo model.
    # The FK is nullable because a response can exist without a file.
    archivo = models.ForeignKey(
        "tramites.Archivo",
        on_delete=models.PROTECT,
        related_name="respuesta_archivos",
        null=True,
        blank=True,
        verbose_name="Archivo",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoRespuesta.choices,
        default=EstadoRespuesta.BORRADOR,
        verbose_name="Estado",
        help_text="Borrador, emitida, anulada, rectificada.",
    )
    fecha_emision = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Emisión",
        help_text="Momento real de emisión.",
    )
    emitido_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="respuestas_emitidas",
        verbose_name="Emitido por",
        help_text="Usuario que ejecutó la emisión. Nullable para BORRADOR.",
        null=True,
        blank=True,
    )
    version = models.PositiveIntegerField(
        default=1,
        verbose_name="Versión",
        help_text="Si existe versionado.",
    )
    observacion = models.TextField(
        null=True,
        blank=True,
        verbose_name="Observación",
        help_text="Complemento.",
    )

    class Meta:
        db_table = "asignaciones_solicitud_asignacion_respuesta"
        verbose_name = "Respuesta de Asignación"
        verbose_name_plural = "Respuestas de Asignación"
        ordering = ["-fecha_emision"]

    def __str__(self):
        return f"Respuesta {self.periodo} — {self.tipo_respuesta}"

    @property
    def esta_emitida(self):
        """True if this response has been officially issued."""
        return self.estado == EstadoRespuesta.EMITIDA and self.fecha_emision is not None
