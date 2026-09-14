"""
SolicitudRespuesta — Respuesta formal institucional a una Solicitud.

A diferencia de SolicitudAsignacionRespuesta (período), esta es la respuesta
a nivel de solicitud. El contenido/conclusión institucional. Se emite como
acto formal de cierre. Los archivos van en MensajeArchivoAdjunto via SISTEMA
mensaje en la Conversacion asociada.
"""

from django.db import models

from core.models import BaseModel
from modules.usuarios.domain.models.usuario import Usuario

from modules.asignaciones.domain.constants import TipoRespuesta


class SolicitudRespuesta(BaseModel):
    """
    Respuesta formal institucional a una Solicitud.

    Se emite como acto formal de cierre. Solo puede haber una respuesta
    con es_final=True por Solicitud (constraint a nivel de aplicación;
    se valida en el flujo antes de crear).
    """

    solicitud = models.ForeignKey(
        "tramites.Solicitud",
        on_delete=models.CASCADE,
        related_name="respuestas",
        verbose_name="Solicitud",
    )
    conversacion = models.ForeignKey(
        "conversaciones.Conversacion",
        on_delete=models.PROTECT,
        related_name="respuestas_solicitud",
        verbose_name="Conversación",
    )
    mensaje = models.ForeignKey(
        "conversaciones.Mensaje",
        on_delete=models.PROTECT,
        related_name="respuestas_solicitud",
        verbose_name="Mensaje",
    )
    area = models.ForeignKey(
        "usuarios.Area",
        on_delete=models.PROTECT,
        related_name="respuestas_solicitud",
        verbose_name="Área",
    )
    periodo = models.ForeignKey(
        "asignaciones.SolicitudAsignacionPeriodo",
        on_delete=models.SET_NULL,
        related_name="respuestas_solicitud",
        verbose_name="Período",
        null=True,
        blank=True,
    )
    tipo_respuesta = models.CharField(
        max_length=20,
        choices=TipoRespuesta.choices,
        verbose_name="Tipo de Respuesta",
    )
    contenido = models.TextField(
        null=True,
        blank=True,
        verbose_name="Contenido de la respuesta",
    )
    es_final = models.BooleanField(
        default=False,
        verbose_name="¿Es la respuesta final de cierre?",
        help_text="True = esta respuesta cierra la solicitud",
    )
    fecha_emision = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Emisión",
    )
    emitido_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="respuestas_solicitud_emitidas",
        verbose_name="Emitido por",
    )

    class Meta:
        db_table = "tramites_solicitud_respuesta"
        verbose_name = "Respuesta de Solicitud"
        verbose_name_plural = "Respuestas de Solicitud"
        ordering = ["-fecha_emision"]

    def __str__(self):
        return f"SolicitudRespuesta {self.id} — {self.tipo_respuesta} ({'final' if self.es_final else 'parcial'})"
