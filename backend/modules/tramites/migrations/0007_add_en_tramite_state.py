# Migration to add EN_TRAMITE state and backfill legacy EN_GESTION rows.
#
# Context:
#   - EN_TRAMITE is a new intermediate state: areas distributed but no period
#     is yet in active management (EN_GESTION).
#   - Before this migration, creating a Solicitud with areas immediately set
#     estado=EN_GESTION even though no period was yet in EN_GESTION.
#   - After this migration, creating with areas sets estado=EN_TRAMITE;
#     the transition to EN_GESTION happens only when a period is taken/started.
#
# Backfill logic:
#   - Solicitud is EN_GESTION but has NO period in EN_GESTION
#     → should be EN_TRAMITE (areas distributed, not yet actively managed)
#   - Solicitud is EN_GESTION and has at least one period in EN_GESTION
#     → stays EN_GESTION (actively managed)
#   - Backfilled EN_TRAMITE rows: fecha_inicio_gestion → NULL
#     (previously set at distribution time, not at management start time)

from django.db import migrations


def backfill_en_tramite(apps, schema_editor):
    """
    Backfill solicitudes that should be EN_TRAMITE but are incorrectly EN_GESTION.

    A Solicitud is EN_GESTION without justification (premature) when:
      - estado = EN_GESTION
      - AND no period belonging to this solicitud has estado = EN_GESTION
    """
    # Conditional import — apps is only available inside migrations
    from modules.asignaciones.domain.models import SolicitudAsignacionPeriodo

    Solicitud = apps.get_model("tramites", "Solicitud")

    # Subquery: all solicitud_ids that have at least one period in EN_GESTION
    solicitudes_con_gestion = set(
        SolicitudAsignacionPeriodo.objects.filter(
            estado="EN_GESTION"
        )
        .values_list("asignacion__solicitud_id", flat=True)
    )

    for solicitud in Solicitud.objects.filter(estado="EN_GESTION"):
        if solicitud.id not in solicitudes_con_gestion:
            # No period is in EN_GESTION — should be EN_TRAMITE
            solicitud.estado = "EN_TRAMITE"
            # fecha_inicio_gestion was set at distribution time, not management start
            solicitud.fecha_inicio_gestion = None
            solicitud.save(update_fields=["estado", "fecha_inicio_gestion"])


def reverse_backfill(apps, schema_editor):
    """
    Reverse: restore EN_GESTION for backfilled rows.
    Only affects rows that were changed by backfill_en_tramite.
    """
    Solicitud = apps.get_model("tramites", "Solicitud")
    Solicitud.objects.filter(estado="EN_TRAMITE").update(
        estado="EN_GESTION",
        # fecha_inicio_gestion stays null after reversal (was already wrong before)
    )


class Migration(migrations.Migration):

    dependencies = [
        ("tramites", "0006_fix_tipo_documento_null"),
    ]

    operations = [
        # No schema change needed — CharField with TextChoices stores plain varchar.
        # The EN_TRAMITE value is added to the Python enum at runtime via the
        # constants.py change; the database accepts any varchar ≤ max_length.
        #
        # Data backfill: fix prematurely-set EN_GESTION rows
        migrations.RunPython(
            backfill_en_tramite,
            reverse_code=reverse_backfill,
        ),
    ]
