from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tramites", "0008_alter_historicalexpediente_tipo_documento_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="expedientearchivo",
            name="archivo",
            field=models.FileField(
                max_length=1024,
                upload_to="tramites/expedientes/",
                verbose_name="Archivo",
            ),
        ),
        migrations.AlterField(
            model_name="solicitudarchivo",
            name="archivo",
            field=models.FileField(
                max_length=1024,
                upload_to="tramites/solicitudes/",
                verbose_name="Archivo",
            ),
        ),
    ]
