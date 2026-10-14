"""
dump_data_sql — emite SOLO los INSERT de las tablas de dominio
para sembrar un servidor real de produccion a partir de la corrida local
del comando `migracion_datos_legacy`.

NO emite CREATE TABLE, ALTER TABLE ni sentencias de migracion. El schema
del destino debe estar creado previamente con:

    python manage.py migrate

Uso:
    python manage.py dump_data_sql --output data.sql

Genera un archivo .sql listo para correr en el servidor de produccion:

    psql -U postgres -d tramite_documentario_db -f data.sql

El script es idempotente: cada INSERT usa ON CONFLICT (id) DO NOTHING,
asi puede ejecutarse varias veces sin duplicar datos.

Excluye tablas de historia (django-simple-history) y de runtime
(django_q, django_session, token_blacklist, django_admin_log) porque
se regeneran al levantar el servicio.
"""
import datetime
import json
import uuid
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


# Tablas a excluir del dump — todas son derivadas o de runtime.
EXCLUDED_TABLES = {
    "django_migrations",
    "django_admin_log",
    "django_session",
    "token_blacklist_blacklistedtoken",
    "token_blacklist_outstandingtoken",
    "django_q_ormq",
    "django_q_schedule",
    "django_q_task",
    "tramites_historicalarchivo",
    "tramites_historicalexpediente",
    "tramites_historicalsolicitud",
    "usuarios_historicalusuario",
    "usuarios_historicalcapitulo",
    "usuarios_historicalespecialidadingeniero",
    "usuarios_historicalespecialidadrevision",
    "usuarios_historicalingenierohabilitacion",
    "usuarios_historicalperfilingeniero",
}


def _discover_domain_tables(cursor):
    """
    Devuelve la lista de tablas de dominio (no auth, no django_q, no
    history, no runtime) en orden topologico por dependencias FK.

    Se descubre desde information_schema en vez de hardcodearse, para
    mantenerse sincronizada con cualquier migracion que agregue o
    renombre tablas.
    """
    # Tablas que no son del dominio de negocio y deben excluirse del dump.
    NON_DOMAIN_PREFIXES = (
        "django_",
        "token_",
        "auth_",
        "django_q_",
    )
    # django-simple-history nombra sus tablas como <app>_<model>historical
    # o <app>_historical<model>. Cubrimos ambos patrones.
    HISTORY_PATTERNS = (
        "_historical",  # tramites_historicalarchivo, etc.
    )

    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """
    )
    all_tables = {row[0] for row in cursor.fetchall()}

    domain = {
        t
        for t in all_tables
        if not any(t.startswith(p) for p in NON_DOMAIN_PREFIXES)
        and not any(p in t for p in HISTORY_PATTERNS)
    }

    # Construir grafo de dependencias FK.
    cursor.execute(
        """
        SELECT
            tc.table_name,
            ccu.table_name AS referenced_table
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
        """
    )
    fk_edges = list(cursor.fetchall())

    # Orden topologico (Kahn).
    in_degree = {t: 0 for t in domain}
    deps = {t: set() for t in domain}
    for child, parent in fk_edges:
        if child in domain and parent in domain and child != parent:
            if parent not in deps[child]:
                deps[child].add(parent)
                in_degree[child] += 1

    pending = [t for t in sorted(domain) if in_degree[t] == 0]
    ordered = []
    while pending:
        nxt = pending.pop(0)
        ordered.append(nxt)
        for child in domain:
            if nxt in deps[child]:
                deps[child].discard(nxt)
                in_degree[child] -= 1
                if in_degree[child] == 0 and child not in ordered and child not in pending:
                    pending.append(child)

    return ordered


def _format_value(value, conn):
    """Serializa un valor de Python a su representacion literal SQL."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, datetime.datetime):
        # Usar UTC ISO para evitar drift de zona horaria en el destino.
        return f"'{value.isoformat()}'::timestamptz"
    if isinstance(value, datetime.date):
        return f"'{value.isoformat()}'::date"
    if isinstance(value, datetime.time):
        return f"'{value.isoformat()}'::time"
    if isinstance(value, (dict, list)):
        return f"'{json.dumps(value, default=str, ensure_ascii=False)}'::jsonb"
    if isinstance(value, (bytes, memoryview)):
        return f"'\\\\x{bytes(value).hex()}'::bytea"
    if isinstance(value, uuid.UUID):
        return f"'{value}'::uuid"
    # String u otro: escapar comillas simples.
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _table_columns(cursor, table_name):
    """Devuelve la lista de columnas de la tabla en el orden del schema."""
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    return [row[0] for row in cursor.fetchall()]


def _table_count(cursor, table_name):
    cursor.execute(f"SELECT count(*) FROM {table_name}")
    return cursor.fetchone()[0]


class Command(BaseCommand):
    help = (
        "Emite un script SQL con los INSERT de las tablas de dominio. "
        "El script NO contiene CREATE TABLE; el schema destino debe existir "
        "(python manage.py migrate)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="dump_data.sql",
            help="Archivo destino del SQL (default: dump_data.sql).",
        )
        parser.add_argument(
            "--include-empty",
            action="store_true",
            help="Incluir tablas con 0 filas en el header informativo.",
        )

    def handle(self, *args, **options) -> None:
        output_path = Path(options["output"]).resolve()
        include_empty = options["include_empty"]

        out = StringIO()
        out.write(
            "-- =====================================================================\n"
            "-- dump_data_sql: INSERTs de las tablas de dominio (data-only)\n"
            f"-- Generado: {datetime.datetime.now().isoformat()}\n"
            f"-- Origen: {settings.DATABASES['default']['HOST']}:"
            f"{settings.DATABASES['default']['PORT']}/"
            f"{settings.DATABASES['default']['NAME']}\n"
            "-- Schema destino debe estar creado (python manage.py migrate).\n"
            "-- Cada INSERT usa ON CONFLICT (id) DO NOTHING — re-ejecutable.\n"
            "-- =====================================================================\n\n"
        )

        with connection.cursor() as cursor:
            table_order = _discover_domain_tables(cursor)
            self.stdout.write(self.style.WARNING(
                f"Tablas de dominio detectadas: {len(table_order)}"
            ))
            tables_present = []
            for table in table_order:
                try:
                    cnt = _table_count(cursor, table)
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(
                        f"  Skipping {table}: {exc}"
                    ))
                    continue
                if cnt == 0 and not include_empty:
                    continue
                tables_present.append((table, cnt))

            out.write("-- =====================================================================\n")
            out.write("-- Resumen\n")
            out.write("-- =====================================================================\n")
            for table, cnt in tables_present:
                out.write(f"-- {table}: {cnt} filas\n")
            out.write("\n")

            total_rows = 0
            for table, expected in tables_present:
                out.write(f"\n-- ============================================================\n")
                out.write(f"-- {table} ({expected} filas)\n")
                out.write(f"-- ============================================================\n")
                cols = _table_columns(cursor, table)
                conflict_target = "id" if "id" in cols else "ctid"
                select_sql = f"SELECT {', '.join(cols)} FROM {table} ORDER BY 1"
                cursor.execute(select_sql)
                written = 0
                for row in cursor.fetchall():
                    values = ", ".join(
                        _format_value(v, connection) for v in row
                    )
                    out.write(
                        f"INSERT INTO {table} ({', '.join(cols)}) "
                        f"VALUES ({values}) "
                        f"ON CONFLICT ({conflict_target}) DO NOTHING;\n"
                    )
                    written += 1
                total_rows += expected
                self.stdout.write(self.style.SUCCESS(
                    f"  {table}: {expected} filas, {written} INSERTs"
                ))

        # Las PK son UUID → no hay secuencias que resetear.
        # Si en el futuro se agrega alguna tabla con SERIAL, se debe
        # agregar el reset especifico aca.

        out.write("\n")
        out.write(
            "-- =====================================================================\n"
            "-- Notas de uso\n"
            "-- =====================================================================\n"
            f"-- 1. Aplicar schema: python manage.py migrate\n"
            f"-- 2. Cargar data:   psql -U postgres -d <db> -f {output_path.name}\n"
            f"-- 3. Total filas:  {total_rows}\n"
            f"-- 4. Idempotente:  cada INSERT usa ON CONFLICT (id) DO NOTHING.\n"
            f"-- 5. Excluye tablas de historia (django-simple-history) y runtime\n"
            f"--    (django_q, django_session, token_blacklist, django_admin_log).\n"
        )

        output_path.write_text(out.getvalue(), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(
            f"\nDump SQL escrito en: {output_path} ({total_rows} filas, "
            f"{len(tables_present)} tablas)"
        ))
