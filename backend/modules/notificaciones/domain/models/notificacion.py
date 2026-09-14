"""
Notificacion y NotificacionUsuario — Eventos comunicados al área.

Notificacion es del área, no del usuario individual.
NotificacionArea codifica la audiencia institucional por área.
NotificacionUsuario rastrea quién podía ver la notificación y quién la vio.

Notificacion.estado fue eliminado — el estado individual vive en NotificacionUsuario.
"""

from django.db import models

from core.models import BaseModel
from modules.usuarios.domain.models import Area, Usuario

from ..constants import AmbitoNotificacion, EventoNotificacion, PrioridadNotificacion


class Notificacion(BaseModel):
    """
    Evento que se comunica al Área.

    La notificación es del Área, no de Juan, Pedro o María.
    NotificacionArea codifica la audiencia institucional por área.
    NotificacionUsuario codifica la audiencia por usuario directo.

    Campos clave:
    - ambito: discriminador de dominio (SOLICITUD, SISTEMA)
    - evento: código de evento dentro del ámbito
    - prioridad: NORMAL, ALTA, CRITICA
    - titulo:快照 del título al momento de creación
    - mensaje: texto opcional
    - generada_por: usuario que provocó el evento
    - ocurrido_en: fecha/hora real del evento (distinto de created_at)
    """

    ambito = models.CharField(
        max_length=30,
        default=AmbitoNotificacion.SOLICITUD,
        verbose_name="Ámbito",
        help_text="Dominio/discriminador: SOLICITUD, SISTEMA",
    )
    evento = models.CharField(
        max_length=30,
        verbose_name="Evento",
        help_text="Código de evento dentro del ámbito.",
    )
    prioridad = models.CharField(
        max_length=20,
        default=PrioridadNotificacion.DEFAULT,
        verbose_name="Prioridad",
        help_text="NORMAL, ALTA, CRITICA.",
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
    ocurrido_en = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Ocurrido en",
        help_text="Fecha/hora real del evento que dispara la notificación.",
    )

    class Meta:
        db_table = "asignaciones_notificacion"
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ambito}/{self.evento} — {self.titulo}"


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


class NotificacionArea(BaseModel):
    """
    Relación entre Notificacion y su audiencia institucional Área.
    """

    notificacion = models.ForeignKey(
        Notificacion,
        on_delete=models.CASCADE,
        related_name="areas_notificadas",
        verbose_name="Notificación",
    )
    area = models.ForeignKey(
        Area,
        on_delete=models.CASCADE,
        related_name="notificaciones_como_audiencia",
        verbose_name="Área",
    )

    class Meta:
        db_table = "asignaciones_notificacion_area"
        verbose_name = "Área de Notificación"
        verbose_name_plural = "Áreas de Notificación"
        constraints = [
            models.UniqueConstraint(
                fields=["notificacion", "area"],
                name="unique_notificacion_area",
            ),
        ]

    def __str__(self):
        return f"{self.notificacion} → {self.area}"
