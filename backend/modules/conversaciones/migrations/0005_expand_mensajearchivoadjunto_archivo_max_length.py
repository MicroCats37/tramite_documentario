from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conversaciones", "0004_rename_cerrada_por_conversacion_cerrado_por_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mensajearchivoadjunto",
            name="archivo",
            field=models.FileField(
                max_length=1024,
                verbose_name="Archivo",
            ),
        ),
    ]
