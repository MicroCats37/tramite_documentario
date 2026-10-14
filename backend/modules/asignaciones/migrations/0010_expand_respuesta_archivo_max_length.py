from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("asignaciones", "0009_alter_solicitudasignacionperiodoestadohistorial_origen"),
    ]

    operations = [
        migrations.AlterField(
            model_name="solicitudasignacionrespuesta",
            name="archivo",
            field=models.FileField(
                max_length=1024,
                null=True,
                blank=True,
                upload_to="asignaciones/respuestas/",
                verbose_name="Archivo",
                help_text="Documento oficial.",
            ),
        ),
    ]
