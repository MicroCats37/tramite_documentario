"""
Comando para sembrar tipos de documento desde seeds/tipo_documento.json.

Idempotente: usa get_or_create por nombre.

Uso:
    python manage.py seed_tipo_documento
    python manage.py seed_tipo_documento --dry-run
"""

import json
from pathlib import Path
from typing import Optional

from django.db import transaction
from django.core.management.base import BaseCommand

from modules.tramites.domain.models.tipo_documento import TipoDocumento


class Command(BaseCommand):
    help = "Siembra tipos de documento desde seeds/tipo_documento.json"

    SEEDS_DIR = Path(__file__).resolve().parent / "seeds"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )
        parser.add_argument(
            "--seed-path",
            type=Path,
            default=None,
            help="Ruta alternativa al JSON de tipos de documento.",
        )

    def handle(self, *args, **options) -> None:
        dry_run: bool = options["dry_run"]
        seed_file: Optional[Path] = options["seed_path"]

        if seed_file is None:
            seed_file = self.SEEDS_DIR / "tipo_documento.json"

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

        tipos_raw: list[dict[str, str]] = data

        creados: int = 0
        existentes: int = 0

        for item in tipos_raw:
            nombre: str = item["nombre"]
            descripcion: str = item.get("descripcion", "")

            defaults: dict[str, str] = {
                "descripcion": descripcion,
            }

            if dry_run:
                self.stdout.write(
                    f"[DRY] TipoDocumento: {nombre} | descripcion: {descripcion}"
                )
                continue

            with transaction.atomic():
                _, was_created = TipoDocumento.objects.get_or_create(
                    nombre=nombre,
                    defaults=defaults,
                )
                if was_created:
                    creados += 1
                else:
                    existentes += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: {len(tipos_raw)} tipos de documento validados en el JSON."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"TipoDocumento: {creados} creados, {existentes} ya existentes | "
                    f"Total en JSON: {len(tipos_raw)}"
                )
            )
