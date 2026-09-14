# Migration for SolicitudRespuesta model

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tramites", "0004_add_tipo_documento_model"),
    ]

    operations = [
        migrations.CreateModel(
            name="SolicitudRespuesta",
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
                    "tipo_respuesta",
                    models.CharField(
                        choices=[
                            ("FINAL", "Final"),
                            ("PARCIAL", "Parcial"),
                            ("INFORME", "Informe"),
                            ("OBSERVACION", "Observación"),
                            ("ACLARACION", "Aclaración"),
                            ("CANCELACION", "Cancelación"),
                        ],
                        max_length=20,
                        verbose_name="Tipo de Respuesta",
                    ),
                ),
                (
                    "contenido",
                    models.TextField(
                        blank=True,
                        null=True,
                        verbose_name="Contenido de la respuesta",
                    ),
                ),
                (
                    "es_final",
                    models.BooleanField(
                        default=False,
                        help_text="True = esta respuesta cierra la solicitud",
                        verbose_name="¿Es la respuesta final de cierre?",
                    ),
                ),
                (
                    "fecha_emision",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Fecha de Emisión",
                    ),
                ),
                (
                    "solicitud",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="respuestas",
                        to="tramites.solicitud",
                        verbose_name="Solicitud",
                    ),
                ),
                (
                    "conversacion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="respuestas_solicitud",
                        to="conversaciones.conversacion",
                        verbose_name="Conversación",
                    ),
                ),
                (
                    "mensaje",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="respuestas_solicitud",
                        to="conversaciones.mensaje",
                        verbose_name="Mensaje",
                    ),
                ),
                (
                    "area",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="respuestas_solicitud",
                        to="usuarios.area",
                        verbose_name="Área",
                    ),
                ),
                (
                    "periodo",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="respuestas_solicitud",
                        to="asignaciones.solicitudasignacionperiodo",
                        verbose_name="Período",
                    ),
                ),
                (
                    "emitido_por",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="respuestas_solicitud_emitidas",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Emitido por",
                    ),
                ),
            ],
            options={
                "db_table": "tramites_solicitud_respuesta",
                "ordering": ["-fecha_emision"],
                "verbose_name": "Respuesta de Solicitud",
                "verbose_name_plural": "Respuestas de Solicitud",
            },
        ),
    ]
