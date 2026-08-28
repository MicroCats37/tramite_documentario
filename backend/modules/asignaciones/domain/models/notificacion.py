"""
Notificacion y NotificacionUsuario — Eventos comunicados al área.

Notificacion es del área, no del usuario individual.
NotificacionUsuario rastrea quién podía ver la notificación y quién la vio.
"""

from django.db import models

from core.models import BaseModel
from modules.usuarios.domain.models import Area, Usuario

from ..constants import EstadoNotificacion, TipoNotificacion


class Notificacion(BaseModel):
    """
    Evento que se comunica al Área.

    La notificación es del Área, no de Juan, Pedro o María.
    """

    area = models.ForeignKey(
        Area,
        on_delete=models.CASCADE,
        related_name="notificaciones",
        verbose_name="Área Destinataria",
    )
    tipo = models.CharField(
        max_length=30,
        choices=TipoNotificacion.choices,
        default=TipoNotificacion.NUEVA_ASIGNACION,
        verbose_name="Tipo",
        help_text="Nueva asignación, devolución, comentario, etc.",
    )
    solicitud = models.ForeignKey(
        "tramites.Solicitud",
        on_delete=models.CASCADE,
        related_name="notificaciones",
        verbose_name="Solicitud",
        null=True,
        blank=True,
    )
    asignacion = models.ForeignKey(
        "asignaciones.SolicitudAsignacion",
        on_delete=models.CASCADE,
        related_name="notificaciones",
        verbose_name="Asignación",
        null=True,
        blank=True,
    )
    periodo = models.ForeignKey(
        "asignaciones.SolicitudAsignacionPeriodo",
        on_delete=models.CASCADE,
        related_name="notificaciones",
        verbose_name="Período",
        null=True,
        blank=True,
    )
    titulo = models.CharField(
        max_length=200,
        verbose_name="Título",
    )
    mensaje = models.TextField(
        null=True,
        blank=True,
        verbose_name="Mensaje",
        help_text="Detalle.",
    )
    generada_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="notificaciones_generadas",
        verbose_name="Generada por",
        null=True,
        blank=True,
        help_text="Actor que provocó el evento.",
    )
    fecha_evento = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha del Evento",
        help_text="Fecha real si necesitas importar eventos históricos.",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoNotificacion.choices,
        default=EstadoNotificacion.PENDIENTE,
        verbose_name="Estado",
    )

    class Meta:
        db_table = "asignaciones_notificacion"
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tipo} — {self.area} — {self.titulo}"


class NotificacionUsuario(BaseModel):
    """
    Quién podía ver la notificación y quién efectivamente la vio.

    Ejemplo: Notificación #500 para Área Arquitectura.
    Juan la vio a las 08:10, Pedro no la ha visto, María la vio a las 08:16.
    """

    notificacion = models.ForeignKey(
        Notificacion,
        on_delete=models.CASCADE,
        related_name="usuarios_notificados",
        verbose_name="Notificación",
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="notificaciones_recibidas",
        verbose_name="Usuario Destinatario",
    )
    vista_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Vista en",
        help_text="Cuándo abrió/vio la notificación.",
    )
    abierta_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Abierta en",
        help_text="Si distingues vista de entrada al detalle.",
    )
    descartada_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Descartada en",
        help_text="Si existe esa acción.",
    )

    class Meta:
        db_table = "asignaciones_notificacion_usuario"
        verbose_name = "Usuario de Notificación"
        verbose_name_plural = "Usuarios de Notificación"
        ordering = ["notificacion", "usuario"]
        constraints = [
            models.UniqueConstraint(
                fields=["notificacion", "usuario"],
                name="unique_notificacion_usuario",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} — {self.notificacion}"

    @property
    def fue_vista(self):
        """True if this user has seen the notification."""
        return self.vista_at is not None

    @property
    def fue_abierta(self):
        """True if this user opened the notification details."""
        return self.abierta_at is not None
