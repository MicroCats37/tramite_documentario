# Safe state-only migration removing notification models from asignaciones.
#
# Uses SeparateDatabaseAndState with empty database_operations to remove
# the notification models from Django's migration state WITHOUT dropping
# any physical database tables.
#
# The physical tables (asignaciones_notificacion, etc.) already exist
# and are now owned by the 'notificaciones' app (via its 0001_initial).
# We only remove the model state from 'asignaciones' so Django's
# autodetector stops thinking this app owns those models.
#
# No DDL is executed — tables remain intact.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("asignaciones", "0007_notificacion_periodo"),
    ]

    state_operations = [
        migrations.DeleteModel(name="Notificacion"),
        migrations.DeleteModel(name="NotificacionUsuario"),
        migrations.DeleteModel(name="NotificacionArea"),
        migrations.DeleteModel(name="NotificacionSolicitud"),
        migrations.DeleteModel(name="NotificacionAsignacion"),
        migrations.DeleteModel(name="NotificacionPeriodo"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=state_operations,
        ),
    ]
