"""
Add descripcion field to MensajeArchivoAdjunto.

Revision ID: 0002_add_descripcion_to_mensajearchivoadjunto
Revises: 0001_initial
Create Date: 2026-09-09
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conversaciones", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="mensajearchivoadjunto",
            name="descripcion",
            field=models.CharField(
                blank=True,
                max_length=500,
                null=True,
                verbose_name="Descripción",
            ),
        ),
    ]
