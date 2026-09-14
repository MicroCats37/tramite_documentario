# Safe initial migration for notificaciones.
#
# Uses SeparateDatabaseAndState to register model state in Django's migration
# graph WITHOUT creating/dropping physical tables.
# The notification tables already exist under the asignaciones app's migrations.
# We tell Django "these models exist in the database" without running any DDL.
#
# db_table names are preserved to match the physical tables:
#   asignaciones_notificacion, asignaciones_notificacion_usuario,
#   asignaciones_notificacion_area, asignaciones_notificacion_solicitud,
#   asignaciones_notificacion_asignacion, asignaciones_notificacion_periodo

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("usuarios", "0002_area_cargo_asignacionusuario"),
        ("tramites", "0001_initial"),
    ]

    state_operations = [
        migrations.CreateModel(
            name="Notificacion",
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
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Fecha de creación",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="Última actualización",
                    ),
                ),
                (
                    "area",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="notificaciones",
                        to="usuarios.area",
                        verbose_name="Área Destinataria",
                    ),
                ),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("NUEVA_ASIGNACION", "Nueva Asignación"),
                            ("DEVOLUCION", "Devolución"),
                            ("COMENTARIO", "Comentario"),
                            ("RESPUESTA", "Respuesta"),
                            ("RECORDATORIO", "Recordatorio"),
                            ("URGENTE", "Urgente"),
                        ],
                        default="NUEVA_ASIGNACION",
                        help_text="Nueva asignación, devolución, comentario, etc.",
                        max_length=30,
                        verbose_name="Tipo",
                    ),
                ),
                (
                    "solicitud",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.CASCADE,
                        related_name="notificaciones",
                        to="tramites.solicitud",
                        verbose_name="Solicitud",
                    ),
                ),
                (
                    "asignacion",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.CASCADE,
                        related_name="notificaciones",
                        to="asignaciones.solicitudasignacion",
                        verbose_name="Asignación",
                    ),
                ),
                (
                    "periodo",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.CASCADE,
                        related_name="notificaciones",
                        to="asignaciones.solicitudasignacionperiodo",
                        verbose_name="Período",
                    ),
                ),
                (
                    "titulo",
                    models.CharField(max_length=200, verbose_name="Título"),
                ),
                (
                    "mensaje",
                    models.TextField(
                        blank=True,
                        null=True,
                        verbose_name="Mensaje",
                        help_text="Detalle.",
                    ),
                ),
                (
                    "generada_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.PROTECT,
                        related_name="notificaciones_generadas",
                        to="usuarios.usuario",
                        verbose_name="Generada por",
                        help_text="Actor que provocó el evento.",
                    ),
                ),
                (
                    "fecha_evento",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="Fecha del Evento",
                        help_text="Fecha real si necesitas importar eventos históricos.",
                    ),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("PENDIENTE", "Pendiente"),
                            ("ENVIADA", "Enviada"),
                            ("LEIDA", "Leída"),
                            ("DESCARTADA", "Descartada"),
                        ],
                        default="PENDIENTE",
                        max_length=20,
                        verbose_name="Estado",
                    ),
                ),
                (
                    "tipo_evento",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("NUEVA_ASIGNACION", "Nueva Asignación"),
                            ("DEVOLUCION", "Devolución"),
                            ("COMENTARIO", "Comentario"),
                            ("RESPUESTA", "Respuesta"),
                            ("RECORDATORIO", "Recordatorio"),
                            ("URGENTE", "Urgente"),
                        ],
                        default="NUEVA_ASIGNACION",
                        help_text="Código de evento de la notificación.",
                        max_length=30,
                        null=True,
                        verbose_name="Tipo de Evento",
                    ),
                ),
                (
                    "audiencia_tipo",
                    models.CharField(
                        blank=True,
                        choices=[("AREA", "Área"), ("USUARIO", "Usuario")],
                        default="AREA",
                        help_text="Indica si la audiencia es un área o un usuario directo.",
                        max_length=20,
                        null=True,
                        verbose_name="Tipo de Audiencia",
                    ),
                ),
            ],
            options={
                "verbose_name": "Notificación",
                "verbose_name_plural": "Notificaciones",
                "db_table": "asignaciones_notificacion",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="NotificacionUsuario",
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
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Fecha de creación",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="Última actualización",
                    ),
                ),
                (
                    "notificacion",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="usuarios_notificados",
                        to="notificaciones.notificacion",
                        verbose_name="Notificación",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="notificaciones_recibidas",
                        to="usuarios.usuario",
                        verbose_name="Usuario Destinatario",
                    ),
                ),
                (
                    "vista_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="Vista en",
                        help_text="Cuándo abrió/vio la notificación.",
                    ),
                ),
                (
                    "abierta_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="Abierta en",
                        help_text="Si distingues vista de entrada al detalle.",
                    ),
                ),
                (
                    "descartada_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="Descartada en",
                        help_text="Si existe esa acción.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Usuario de Notificación",
                "verbose_name_plural": "Usuarios de Notificación",
                "db_table": "asignaciones_notificacion_usuario",
                "ordering": ["notificacion", "usuario"],
            },
        ),
        migrations.AddConstraint(
            model_name="notificacionusuario",
            constraint=models.UniqueConstraint(
                fields=("notificacion", "usuario"),
                name="unique_notificacion_usuario",
            ),
        ),
        migrations.CreateModel(
            name="NotificacionArea",
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
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Fecha de creación",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="Última actualización",
                    ),
                ),
                (
                    "notificacion",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="areas_notificadas",
                        to="notificaciones.notificacion",
                        verbose_name="Notificación",
                    ),
                ),
                (
                    "area",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="notificaciones_como_audiencia",
                        to="usuarios.area",
                        verbose_name="Área",
                    ),
                ),
            ],
            options={
                "verbose_name": "Área de Notificación",
                "verbose_name_plural": "Áreas de Notificación",
                "db_table": "asignaciones_notificacion_area",
            },
        ),
        migrations.AddConstraint(
            model_name="notificacionarea",
            constraint=models.UniqueConstraint(
                fields=("notificacion", "area"),
                name="unique_notificacion_area",
            ),
        ),
        migrations.CreateModel(
            name="NotificacionSolicitud",
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
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Fecha de creación",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="Última actualización",
                    ),
                ),
                (
                    "notificacion",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="contexto_solicitud",
                        to="notificaciones.notificacion",
                        verbose_name="Notificación",
                    ),
                ),
                (
                    "solicitud",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="notificacion_contextos",
                        to="tramites.solicitud",
                        verbose_name="Solicitud",
                    ),
                ),
                (
                    "periodo",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="notificacion_contextos",
                        to="asignaciones.solicitudasignacionperiodo",
                        verbose_name="Período",
                    ),
                ),
            ],
            options={
                "verbose_name": "Contexto de Notificación",
                "verbose_name_plural": "Contextos de Notificación",
                "db_table": "asignaciones_notificacion_solicitud",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="notificacionsolicitud",
            constraint=models.UniqueConstraint(
                fields=("notificacion",),
                name="unique_notificacion_solicitud_context",
            ),
        ),
        migrations.CreateModel(
            name="NotificacionAsignacion",
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
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Fecha de creación",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="Última actualización",
                    ),
                ),
                (
                    "notificacion",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="contexto_asignacion",
                        to="notificaciones.notificacion",
                        verbose_name="Notificación",
                    ),
                ),
                (
                    "asignacion",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="notificacion_contextos",
                        to="asignaciones.solicitudasignacion",
                        verbose_name="Asignación",
                    ),
                ),
            ],
            options={
                "verbose_name": "Contexto de Asignación de Notificación",
                "verbose_name_plural": "Contextos de Asignación de Notificación",
                "db_table": "asignaciones_notificacion_asignacion",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="notificacionasignacion",
            constraint=models.UniqueConstraint(
                fields=("notificacion",),
                name="unique_notificacion_asignacion_context",
            ),
        ),
        migrations.CreateModel(
            name="NotificacionPeriodo",
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
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Fecha de creación",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="Última actualización",
                    ),
                ),
                (
                    "notificacion",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="contexto_periodo",
                        to="notificaciones.notificacion",
                        verbose_name="Notificación",
                    ),
                ),
                (
                    "periodo",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="notificacion_periodo_contextos",
                        to="asignaciones.solicitudasignacionperiodo",
                        verbose_name="Período",
                    ),
                ),
            ],
            options={
                "verbose_name": "Contexto de Período de Notificación",
                "verbose_name_plural": "Contextos de Período de Notificación",
                "db_table": "asignaciones_notificacion_periodo",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="notificacionperiodo",
            constraint=models.UniqueConstraint(
                fields=("notificacion",),
                name="unique_notificacion_periodo_context",
            ),
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=state_operations,
        ),
    ]
