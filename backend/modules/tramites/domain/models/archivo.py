"""
Archivo — Central generic file storage model.

Does NOT use Django FileField. Instead stores storage_backend + storage_reference
as provider-agnostic fields, enabling SAAA, local, and external URL backends.

The storage_reference for SAAA is the archivo_id (not the full pointer string).
The storage_reference for local is the file path.
The storage_reference for external_url is the permanent URL.

Soft-delete via estado + eliminado_at (no SAAA delete API available).
History via django-simple-history.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from modules.usuarios.domain.models.usuario import Usuario


class ArchivoEstado(models.TextChoices):
    DISPONIBLE = "disponible", "Disponible"
    ELIMINADO = "eliminado", "Eliminado"


class ArchivoManager(models.Manager):
    """Default manager for Archivo."""

    def activos(self):
        return self.filter(estado=ArchivoEstado.DISPONIBLE)


class Archivo(BaseModel):
    """
    Central generic file storage model.

    Stores file metadata independently of the storage backend.
    The actual file bytes live in SAAA, local disk, or external URL.

    Soft-delete: set estado=ArchivoEstado.ELIMINADO and eliminado_at.
    No physical deletion from SAAA (delete API not available).
    """

    # ── Storage reference (provider-agnostic) ─────────────────────────────────
    storage_backend = models.SlugField(
        max_length=50,
        db_index=True,
        verbose_name="Storage Backend",
        help_text="Storage provider: saaa, local, external_url",
    )
    storage_reference = models.TextField(
        verbose_name="Storage Reference",
        help_text="Backend-specific identifier: SAAA archivo_id, local path, or URL",
    )
    storage_namespace = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Storage Namespace",
        help_text="Optional grouping context (e.g., app_id for SAAA)",
    )

    # ── Universal metadata ────────────────────────────────────────────────────
    nombre_original = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Nombre Original",
    )
    nombre_mostrado = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Nombre Mostrado",
    )
    extension = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name="Extensión",
    )
    mime_type = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name="Tipo MIME",
    )
    tamano_bytes = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="Tamaño (bytes)",
    )
    checksum_sha256 = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name="Checksum SHA-256",
    )
    storage_metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Storage Metadata",
        help_text="Additional backend-specific data (e.g., SAAA pathRelativo)",
    )

    # ── State ─────────────────────────────────────────────────────────────────
    administrado = models.BooleanField(
        default=True,
        verbose_name="Administrado",
        help_text="False for external URLs managed externally",
    )
    estado = models.CharField(
        max_length=20,
        choices=ArchivoEstado.choices,
        default=ArchivoEstado.DISPONIBLE,
        verbose_name="Estado",
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    subido_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="archivos_subidos",
        null=True,
        blank=True,
        verbose_name="Subido por",
    )
    eliminado_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de eliminación",
    )

    # ── History ────────────────────────────────────────────────────────────────
    history = HistoricalRecords()

    # ── Managers ────────────────────────────────────────────────────────────────
    objects = ArchivoManager()

    class Meta:
        db_table = "tramites_archivo"
        verbose_name = "Archivo"
        verbose_name_plural = "Archivos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.nombre_original or self.storage_reference} ({self.storage_backend})"

    @classmethod
    def from_storage_reference(cls, backend: str, reference: str, **kwargs):
        """
        Factory to create an Archivo from a storage reference + backend.
        Used for backfilling from legacy pointer strings.
        """
        return cls(storage_backend=backend, storage_reference=reference, **kwargs)
