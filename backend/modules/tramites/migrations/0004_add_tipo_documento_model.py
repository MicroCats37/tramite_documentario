# Generated migration for TipoDocumento model + Expediente FK change

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_and_migrate(apps, schema_editor):
    """
    Seed TipoDocumento and backfill Expediente.tipo_documento FK in one step.

    Uses the ORM (apps.get_model) after CreateModel and AddField have updated
    the state, ensuring TipoDocumento is available and the Expediente model
    reflects the new FK field.
    """
    TipoDocumento = apps.get_model("tramites", "TipoDocumento")
    Expediente = apps.get_model("tramites", "Expediente")

    # Seed TipoDocumento values
    values = [
        ("OFICIO", "Oficio"),
        ("CARTA", "Carta"),
        ("SOLICITUD", "Solicitud"),
        ("MEMORANDO", "Memorando"),
        ("INFORME", "Informe"),
        ("EXPEDIENTE", "Expediente"),
        ("RECIBO", "Recibo"),
        ("CERTIFICADO", "Certificado"),
        ("OTRO", "Otro"),
    ]
    tipo_docs = {}
    for nombre, descripcion in values:
        td = TipoDocumento.objects.create(nombre=nombre, descripcion=descripcion)
        tipo_docs[nombre] = td

    # Backfill Expediente.tipo_documento FK
    for exp in Expediente.objects.all():
        old_value = getattr(exp, "tipo_documento", None)
        if old_value and old_value in tipo_docs:
            exp.tipo_documento = tipo_docs[old_value]
            exp.save(update_fields=["tipo_documento"])


def reverse_all(apps, schema_editor):
    """Remove all seeded TipoDocumento records."""
    TipoDocumento = apps.get_model("tramites", "TipoDocumento")
    TipoDocumento.objects.filter(
        nombre__in=[
            "OFICIO", "CARTA", "SOLICITUD", "MEMORANDO",
            "INFORME", "EXPEDIENTE", "RECIBO", "CERTIFICADO", "OTRO",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tramites", "0003_add_idempotency_key"),
    ]

    operations = [
        # ── Step 1: Create TipoDocumento table ───────────────────────────────────
        migrations.CreateModel(
            name="TipoDocumento",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Última actualización"),
                ),
                (
                    "nombre",
                    models.CharField(
                        help_text="Código único, ej. OFICIO, CARTA, SOLICITUD",
                        max_length=20,
                        unique=True,
                        verbose_name="Nombre (código)",
                    ),
                ),
                (
                    "descripcion",
                    models.CharField(
                        help_text="Descripción legible, ej. Oficio, Carta, Solicitud",
                        max_length=100,
                        verbose_name="Descripción",
                    ),
                ),
            ],
            options={
                "db_table": "tramites_tipo_documento",
                "verbose_name": "Tipo de Documento",
                "verbose_name_plural": "Tipos de Documento",
                "ordering": ["nombre"],
            },
        ),

        # ── Step 2: Add nullable FK column to Expediente ─────────────────────────
        migrations.AddField(
            model_name="expediente",
            name="tipo_documento_fk",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="expedientes",
                to="tramites.tipodocumento",
                verbose_name="Tipo de Documento",
            ),
        ),

        # ── Step 3: Alter the historical Expediente table (simple_history) ──────────
        # The HistoricalExpediente table also has tipo_documento and must be updated.
        migrations.AlterField(
            model_name="historicalexpediente",
            name="tipo_documento",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",  # no reverse accessor needed for history
                to="tramites.tipodocumento",
                verbose_name="Tipo de Documento",
            ),
        ),

        # ── Step 4: Remove old CharField ─────────────────────────────────────────
        migrations.RemoveField(
            model_name="expediente",
            name="tipo_documento",
        ),

        # ── Step 5: Rename FK to original name ───────────────────────────────────
        migrations.RenameField(
            model_name="expediente",
            old_name="tipo_documento_fk",
            new_name="tipo_documento",
        ),

        # ── Step 5: Seed TipoDocumento + backfill FK (after schema is stable) ─────
        # By running after RenameField, the model state has tipo_documento as FK,
        # and the database column tipo_documento (FK) exists and can accept values.
        migrations.RunPython(seed_and_migrate, reverse_code=reverse_all),
    ]
