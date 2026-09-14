"""
Mensaje, MensajeArchivoAdjunto, MensajeMencion — Modelos del núcleo de mensajería.

Estos modelos son reutilizables y no conocen al dominio de solicitudes
ni a ningún otro módulo. Los permisos y la lógica de visibilidad
son responsabilidad del módulo consumidor.
"""

from django.db import models

from core.models import BaseModel
from modules.usuarios.domain.models.usuario import Usuario

from ..constants import TipoMensaje


class Mensaje(BaseModel):
    """
    Mensaje individual dentro de una conversación.

    Debe tener contenido de texto o al menos un archivo adjunto (constraint a nivel de aplicación).
    """

    conversacion = models.ForeignKey(
        "Conversacion",
        related_name="mensajes",
        on_delete=models.CASCADE,
        verbose_name="Conversación",
    )
    autor_usuario = models.ForeignKey(
        Usuario,
        related_name="mensajes_enviados",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Autor",
    )
    contenido = models.TextField(
        null=True,
        blank=True,
        verbose_name="Contenido",
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoMensaje.choices,
        default=TipoMensaje.MENSAJE,
        verbose_name="Tipo",
    )
    fecha_envio = models.DateTimeField(
        verbose_name="Fecha de envío",
    )
    mensaje_padre = models.ForeignKey(
        "Mensaje",
        null=True,
        blank=True,
        related_name="respuestas",
        on_delete=models.SET_NULL,
        verbose_name="Mensaje padre",
        help_text="Respuesta a otro mensaje (thread).",
    )
    editado_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de edición",
    )
    eliminado_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de eliminación",
    )
    eliminado_por = models.ForeignKey(
        Usuario,
        null=True,
        blank=True,
        related_name="mensajes_eliminados",
        on_delete=models.PROTECT,
        verbose_name="Eliminado por",
    )

    class Meta:
        db_table = "conversaciones_mensaje"
        verbose_name = "Mensaje"
        verbose_name_plural = "Mensajes"
        ordering = ["fecha_envio"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(tipo="SISTEMA", autor_usuario__isnull=True)
                    | models.Q(
                        tipo__in=["MENSAJE", "RESPUESTA"], autor_usuario__isnull=False
                    )
                ),
                name="chk_mensaje_tipo_autor",
            ),
        ]

    def __str__(self):
        preview = (self.contenido or "")[:50]
        return f"Mensaje {self.id} — {preview}"


class MensajeArchivoAdjunto(BaseModel):
    """
    Archivo adjunto a un mensaje.

    Renombrado desde la versión anterior 'MensajeAdjunto' para ser
    más descriptivo del tipo de contenido que almacena.
    """

    mensaje = models.ForeignKey(
        Mensaje,
        related_name="archivos_adjuntos",
        on_delete=models.CASCADE,
        verbose_name="Mensaje",
    )
    archivo = models.FileField(
        verbose_name="Archivo",
    )
    nombre_original = models.CharField(
        max_length=255,
        verbose_name="Nombre original",
    )
    mime_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Tipo MIME",
    )
    tamano_bytes = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="Tamaño (bytes)",
    )
    subido_por = models.ForeignKey(
        Usuario,
        related_name="archivos_subidos",
        on_delete=models.PROTECT,
        verbose_name="Subido por",
    )
    fecha_archivo = models.DateTimeField(
        verbose_name="Fecha de subida",
    )
    descripcion = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Descripción",
    )

    class Meta:
        db_table = "conversaciones_mensaje_archivo_adjunto"
        verbose_name = "Archivo adjunto"
        verbose_name_plural = "Archivos adjuntos"

    def __str__(self):
        return f"Adjunto {self.id} — {self.nombre_original}"


class MensajeMencion(BaseModel):
    """
    Mención explícita de un usuario dentro de un mensaje.

    Permite notificar a usuarios específicos mencionados con @usuario.
    """

    mensaje = models.ForeignKey(
        Mensaje,
        related_name="menciones",
        on_delete=models.CASCADE,
        verbose_name="Mensaje",
    )
    usuario = models.ForeignKey(
        Usuario,
        related_name="menciones_recibidas",
        on_delete=models.CASCADE,
        verbose_name="Usuario mencionado",
    )

    class Meta:
        db_table = "conversaciones_mensaje_mencion"
        verbose_name = "Mencion"
        verbose_name_plural = "Menciones"
        constraints = [
            models.UniqueConstraint(
                fields=["mensaje", "usuario"],
                name="unique_mensaje_usuario_mencion",
            ),
        ]

    def __str__(self):
        return f"@{self.usuario} en mensaje {self.mensaje_id}"
