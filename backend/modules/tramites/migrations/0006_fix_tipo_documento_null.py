# Migration to fix Expediente.tipo_documento nullable drift and backfill NULL rows.
#
# Context:
#   - 0004_add_tipo_documento_model created a *nullable* FK (null=True, blank=True)
#   - The model was later updated to non-nullable (no null=True, blank=True)
#   - Some rows may have NULL tipo_documento in the database
#   - This migration:
#       1. Backfills NULL rows → TipoDocumento(nombre="OTRO")
#       2. Alters the column to non-nullable to match the current model
#       3. Also fixes HistoricalExpediente to match

import uuid

import django.db.models.deletion
from django.db import migrations, models


def _get_or_create_otro_tipo_documento(tipo_documento_model):
    """
    Safely get or create the OTRO TipoDocumento record.

    OTRO was seeded in 0004, but if this migration runs in a fresh database
    (e.g. test fixture that skipped 0004's RunPython), we create it here with
    the same defaults used in the original seed.
    """
    otro, created = tipo_documento_model.objects.get_or_create(
        nombre="OTRO",
        defaults={"descripcion": "Otro"},
    )
    return otro


def backfill_null_tipo_documento(apps, schema_editor):
    """
    Backfill Expediente rows where tipo_documento IS NULL → OTRO.

    Also handles HistoricalExpediente for the simple_history audit trail.
    """
    Expediente = apps.get_model("tramites", "Expediente")
    HistoricalExpediente = apps.get_model("tramites", "HistoricalExpediente")
    TipoDocumento = apps.get_model("tramites", "TipoDocumento")

    otro = _get_or_create_otro_tipo_documento(TipoDocumento)

    # Backfill live Expediente rows
    updated_exp = Expediente.objects.filter(tipo_documento__isnull=True).update(
        tipo_documento=otro
    )

    # Backfill historical records — HistoricalExpediente also has nullable FK
    # from the 0004 AlterField that set it to null=True, blank=True
    updated_hist = HistoricalExpediente.objects.filter(tipo_documento__isnull=True).update(
        tipo_documento=otro
    )

    # Schema change: make the column non-nullable (will be applied after this
    # RunPython via the AlterField operations below)
    # No return value needed — we just log for visibility
    print(f"[0006_fix_tipo_documento_null] Backfilled {updated_exp} Expediente rows and "
          f"{updated_hist} HistoricalExpediente rows to OTRO.")


def reverse_backfill(apps, schema_editor):
    """
    Reverse: there is no way to restore the original NULL sentinel values,
    so this is a no-op that satisfies RunPython's reverse_code requirement.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tramites", "0005_add_solicitud_respuesta"),
    ]

    operations = [
        # ── Step 1: RunPython backfill NULL rows before making column non-nullable ──
        migrations.RunPython(
            backfill_null_tipo_documento,
            reverse_code=reverse_backfill,
        ),

        # ── Step 2: Make Expediente.tipo_documento non-nullable ──────────────────
        migrations.AlterField(
            model_name="expediente",
            name="tipo_documento",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="expedientes",
                to="tramites.tipodocumento",
                verbose_name="Tipo de Documento",
            ),
        ),

        # ── Step 3: Make HistoricalExpediente.tipo_documento non-nullable ──────────
        migrations.AlterField(
            model_name="historicalexpediente",
            name="tipo_documento",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",  # no reverse accessor for history table
                to="tramites.tipodocumento",
                verbose_name="Tipo de Documento",
            ),
        ),
    ]
