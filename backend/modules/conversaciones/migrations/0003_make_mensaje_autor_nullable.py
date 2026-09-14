"""
Make autor_usuario nullable on Mensaje and add CheckConstraint.

System messages (tipo=SISTEMA) have autor_usuario=None.
Human messages (tipo=MENSAJE/RESPUESTA) require autor_usuario to be set.

Revision ID: 0003_make_mensaje_autor_nullable
Revises: 0002_add_descripcion_to_mensajearchivoadjunto
Create Date: 2026-09-11
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("conversaciones", "0002_add_descripcion_to_mensajearchivoadjunto"),
    ]

    operations = [
        # Make autor_usuario nullable for system messages
        migrations.AlterField(
            model_name="mensaje",
            name="autor_usuario",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.PROTECT,
                related_name="mensajes_enviados",
                to="usuarios.Usuario",
                verbose_name="Autor",
            ),
        ),
        # Add CheckConstraint for tipo/autor invariant
        migrations.AddConstraint(
            model_name="mensaje",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(
                        tipo="SISTEMA",
                        autor_usuario__isnull=True,
                    )
                    | models.Q(
                        tipo__in=["MENSAJE", "RESPUESTA"],
                        autor_usuario__isnull=False,
                    )
                ),
                name="chk_mensaje_tipo_autor",
            ),
        ),
    ]
