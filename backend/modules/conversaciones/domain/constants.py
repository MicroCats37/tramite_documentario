"""
Constants — Choices para el dominio de conversaciones.
"""

from django.db import models


class EstadoConversacion(models.TextChoices):
    """Estados posibles de una conversación."""

    ABIERTA = "ABIERTA", "Abierta"
    CERRADA = "CERRADA", "Cerrada"


class TipoMensaje(models.TextChoices):
    """Tipos de mensaje dentro de una conversación."""

    MENSAJE = "MENSAJE", "Mensaje"
    RESPUESTA = "RESPUESTA", "Respuesta"
    SISTEMA = "SISTEMA", "Sistema"
