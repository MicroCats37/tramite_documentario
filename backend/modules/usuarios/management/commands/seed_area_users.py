"""
Comando para crear usuarios de área (uno por cada área activa).

Idempotente: usa get_or_create por username.
Crea o actualiza un usuario por área con username = slug del nombre de área.

Uso:
    python manage.py seed_area_users
    python manage.py seed_area_users --dry-run
    python manage.py seed_area_users --area "Secretaría General"
"""

import unicodedata
import re
from datetime import date
from pathlib import Path

from django.db import transaction
from django.core.management.base import BaseCommand

from modules.usuarios.domain.models import Usuario, Area, Cargo, AsignacionUsuario


def normalize_slug(value: str) -> str:
    """
    Convert a string to a safe lowercase snake_case slug.
    - Unicode to ASCII (NFD normalization + encode/decode)
    - Spaces, underscores, and non-alphanumeric chars to '_'
    - Collapse multiple '_' to one
    - Strip leading/trailing '_'
    """
    # NFD normalizes accented chars to base char + combining mark; strip marks
    normalized = unicodedata.normalize('NFD', value)
    ascii_str = normalized.encode('ascii', 'ignore').decode('ascii')
    # Lowercase and replace separators with underscore
    slug = re.sub(r'[^a-z0-9]+', '_', ascii_str.lower())
    # Collapse multiple underscores
    slug = re.sub(r'_+', '_', slug)
    return slug.strip('_')


class Command(BaseCommand):
    help = "Crea o actualiza un usuario por cada área activa con username = slug del área"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )
        parser.add_argument(
            "--area",
            type=str,
            default=None,
            help="Procesar solo el área con este nombre exacto.",
        )

    def handle(self, *args, **options) -> None:
        dry_run: bool = options["dry_run"]
        area_nombre: str | None = options.get("area")

        # ── Obtener áreas ──────────────────────────────────────────────────────
        if area_nombre:
            areas = Area.objects.filter(activo=True, nombre=area_nombre)
        else:
            areas = Area.objects.filter(activo=True)

        if not areas.exists():
            self.stdout.write(self.style.WARNING("No se encontraron áreas activas."))
            return

        # ── Obtener/crear Cargo genérico ────────────────────────────────────────
        cargo, cargo_created = None, False
        all_cargos = list(Cargo.objects.filter(activo=True).order_by('created_at'))
        if all_cargos:
            cargo = all_cargos[0]
        else:
            if not dry_run:
                cargo = Cargo.objects.create(
                    nombre="Cargo Genérico",
                    activo=True,
                )
                cargo_created = True
                self.stdout.write(self.style.SUCCESS(
                    f"  Cargo 'Cargo Genérico' creado automáticamente."
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    "  [DRY] No existe cargo activo. Se crearía 'Cargo Genérico'."
                ))

        # ── Procesar cada área ─────────────────────────────────────────────────
        creados = 0
        actualizados = 0
        skipped = 0
        today = date.today()

        for area in areas:
            username = normalize_slug(area.nombre)

            if not dry_run:
                with transaction.atomic():
                    # Crear o obtener usuario
                    user, was_created = Usuario.objects.get_or_create(
                        username=username,
                        defaults={
                            "nombres": area.nombre,
                            "apellidos": "Área",
                            "email": None,
                            "dni": None,
                            "is_active": True,
                            "is_staff": False,
                            "is_superuser": False,
                        },
                    )

                    if was_created:
                        user.set_password("admin")
                        user.save(update_fields=["password", "nombres", "apellidos", "updated_at"])
                        creados += 1
                        self.stdout.write(
                            f"  CREADO: {username} -> {area.nombre}"
                        )
                    else:
                        # Actualizar datos si cambiaron
                        needs_update = False
                        if user.nombres != area.nombre:
                            user.nombres = area.nombre
                            needs_update = True
                        if user.apellidos != "Área":
                            user.apellidos = "Área"
                            needs_update = True
                        if needs_update:
                            user.save(update_fields=["nombres", "apellidos", "updated_at"])
                        actualizados += 1
                        self.stdout.write(
                            f"  ACTUALIZADO: {username} -> {area.nombre}"
                        )

                    # ── Crear/verificar AsignacionUsuario ─────────────────────
                    if cargo:
                        existing_asig = AsignacionUsuario.objects.filter(
                            usuario=user,
                            area=area,
                        ).vigentes().exists()

                        if not existing_asig:
                            AsignacionUsuario.objects.create(
                                usuario=user,
                                area=area,
                                cargo=cargo,
                                periodo_inicio=today,
                                periodo_fin=None,
                            )
                            self.stdout.write(
                                f"    -> Asignacion creada: {user.username} -> {area.nombre} / {cargo.nombre}"
                            )
                        else:
                            self.stdout.write(
                                f"    -> Asignacion ya vigente: {user.username} -> {area.nombre}"
                            )
            else:
                # Dry run
                user_exists = Usuario.objects.filter(username=username).exists()
                if user_exists:
                    self.stdout.write(
                        f"  [DRY] ACTUALIZARÍA: {username} -> {area.nombre}"
                    )
                else:
                    self.stdout.write(
                        f"  [DRY] CREADO: {username} -> {area.nombre}"
                    )
                self.stdout.write(
                    f"    -> Asignacion: {username} -> {area.nombre} / {cargo.nombre if cargo else 'N/A'}"
                )

        # ── Resumen ────────────────────────────────────────────────────────────
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: {areas.count()} área(s) validarían."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Usuarios: {creados} creados, {actualizados} actualizados | "
                    f"Total áreas procesadas: {areas.count()}"
                )
            )
