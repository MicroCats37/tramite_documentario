"""
Comando para sembrar áreas institucionales desde seeds/areas.json.

Idempotente: usa get_or_create por nombre.

Uso:
    python manage.py seed_areas
    python manage.py seed_areas --dry-run
    python manage.py seed_areas --reset
    python manage.py seed_areas --deactivate-missing
    python manage.py seed_areas --seed-path=/ruta/personalizada.json
"""

import json
from pathlib import Path
from typing import Optional

from django.db import transaction
from django.core.management.base import BaseCommand

from modules.usuarios.domain.models.area import Area


class Command(BaseCommand):
    help = "Siembra áreas institucionales desde seeds/areas.json"

    SEEDS_DIR = Path(__file__).resolve().parent / "seeds"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Elimina las áreas existentes antes de crear. "
                "Falla si hay AsignacionUsuario activas con PROTECT."
            ),
        )
        parser.add_argument(
            "--seed-path",
            type=Path,
            default=None,
            help="Ruta alternativa al JSON de áreas.",
        )
        parser.add_argument(
            "--deactivate-missing",
            action="store_true",
            help="Marca como activo=False las áreas que existen en BD pero no en el JSON.",
        )

    def handle(self, *args, **options) -> None:
        dry_run: bool = options["dry_run"]
        reset: bool = options["reset"]
        deactivate_missing: bool = options["deactivate_missing"]
        seed_file: Optional[Path] = options["seed_path"]

        if seed_file is None:
            seed_file = self.SEEDS_DIR / "areas.json"

        if not seed_file.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {seed_file}"))
            return

        with open(seed_file, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            self.stdout.write(
                self.style.ERROR(f"El JSON debe ser un array de objetos. Archivo: {seed_file}")
            )
            return

        areas_raw: list[dict[str, str]] = data

        # ── Reset: eliminar áreas existentes ───────────────────────────────────
        if reset:
            if dry_run:
                existing = Area.objects.all()
                self.stdout.write(
                    self.style.WARNING(
                        f"[DRY] Se eliminarían {existing.count()} áreas existentes. "
                        "Se Cancela por --dry-run."
                    )
                )
            else:
                existing_count = Area.objects.count()
                if existing_count > 0:
                    # Verificar integridad referencial con AsignacionUsuario
                    protected_ids: list[int] = list(
                        Area.objects.filter(asignaciones__isnull=False)
                        .distinct()
                        .values_list("id", flat=True)
                    )
                    if protected_ids:
                        self.stdout.write(
                            self.style.ERROR(
                                f"No se puede hacer reset: {len(protected_ids)} área(s) tienen "
                                "AsignacionUsuario activas (PROTECT). "
                                "Reasigna o elimina las asignaciones primero."
                            )
                        )
                        return

                    deleted, _ = Area.objects.all().delete()
                    self.stdout.write(
                        self.style.WARNING(
                            f"Reset: {deleted} áreas eliminadas."
                        )
                    )

        # ── Sincronización: deactivate_missing ───────────────────────────────────
        if deactivate_missing and not dry_run:
            json_nombres: set[str] = {item["nombre"] for item in areas_raw}
            to_deactivate = Area.objects.filter(activo=True).exclude(nombre__in=json_nombres)
            deactivated_count = to_deactivate.update(activo=False)
            if deactivated_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"Desactivadas {deactivated_count} áreas que no están en el JSON."
                    )
                )

        # ── Crear / actualizar áreas ───────────────────────────────────────────
        creados: int = 0
        reactivados: int = 0

        for item in areas_raw:
            nombre: str = item["nombre"]
            descripcion: Optional[str] = item.get("descripcion") or None

            defaults: dict[str, Optional[str]] = {"descripcion": descripcion}

            if dry_run:
                self.stdout.write(
                    f"[DRY] Área: {nombre} | descripcion: {descripcion or '(vacía)'}"
                )
                continue

            with transaction.atomic():
                area, was_created = Area.objects.get_or_create(
                    nombre=nombre,
                    defaults=defaults,
                )
                if not was_created:
                    # Reactivar si estaba inactiva
                    if not area.activo:
                        area.activo = True
                        area.descripcion = descripcion or area.descripcion
                        area.save(update_fields=["activo", "descripcion", "updated_at"])
                        reactivados += 1
                    elif area.descripcion != descripcion:
                        # Sincronizar descripción si cambió
                        area.descripcion = descripcion
                        area.save(update_fields=["descripcion", "updated_at"])
                else:
                    creados += 1

        # ── Resumen ─────────────────────────────────────────────────────────────
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: {len(areas_raw)} áreas validadas en el JSON."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Áreas: {creados} creadas, {reactivados} reactivadas | "
                    f"Total en JSON: {len(areas_raw)}"
                )
            )
