"""
IdempotencyKey — almacena claves de idempotencia para endpoints de creación.

Previene la creación de recursos duplicados cuando el cliente reintenta
un request con la misma clave.
"""

from django.db import models

from core.models import BaseModel
from modules.usuarios.domain.models import Usuario


class IdempotencyKey(BaseModel):
    """
    Almacena el resultado de una operación creada con clave de idempotencia.

    Si arrives un segundo request con la misma clave, se retorna el resultado
    cacheado sin re-ejecutar la lógica de negocio.

    La clave es única por usuario + operación + clave.
    Se expira después de 24 horas.
    """

    key = models.CharField(
        max_length=64,
        verbose_name="Clave de Idempotencia",
        help_text="UUID proporcionado por el cliente en el header Idempotency-Key.",
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="idempotency_keys",
        verbose_name="Usuario",
    )
    endpoint = models.CharField(
        max_length=255,
        verbose_name="Endpoint",
        help_text="Path del endpoint que usa esta clave (ej: /api/solicitudes/crear-completo).",
    )
    result = models.JSONField(
        verbose_name="Resultado Cacheado",
        help_text="Respuesta HTTP serializada (status_code + body).",
    )
    status_code = models.PositiveSmallIntegerField(
        default=200,
        verbose_name="Status HTTP del resultado",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    class Meta:
        db_table = "tramites_idempotency_key"
        verbose_name = "Clave de Idempotencia"
        verbose_name_plural = "Claves de Idempotencia"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "endpoint", "key"],
                name="unique_usuario_endpoint_key",
            ),
        ]

    def __str__(self):
        return f"IdempotencyKey({self.key[:8]}...) - {self.endpoint}"
