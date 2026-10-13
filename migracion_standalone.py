#!/usr/bin/env python3
"""
Standalone ETL script to migrate data from legacy mesa_partes database.

This script connects directly to both databases using psycopg2 and performs
the migration without requiring Django.

Usage:
    python migracion_standalone.py [--dry-run] [--skip-files]
"""
import sys
import json
import uuid
from datetime import date, datetime
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


# Configuration
LEGACY_DB = {
    'host': 'localhost',
    'port': 15433,
    'dbname': 'mesa_partes_db',
    'user': 'postgres',
    'password': 'postgres',
}

NEW_DB = {
    'host': 'localhost',
    'port': 12003,
    'dbname': 'tramite_documentario_db',
    'user': 'tramite_documentario_user',
    'password': 'changeme',
}

# State mapping for solicitudes
STATE_MAP = {
    'CERRADO': 'FINALIZADA',
    'ENVIADO_A_AREA': 'EN_TRAMITE',
    'EN_GESTION_MP': 'EN_GESTION',
    'REENVIO_MP': 'EN_TRAMITE',
}


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Migrate legacy mesa_partes data')
    parser.add_argument('--dry-run', action='store_true', help='Validate without writing')
    parser.add_argument('--skip-files', action='store_true', help='Skip file migration')
    args = parser.parse_args()

    print("=" * 60)
    print("MIGRATION: Standalone ETL (bypasses Django)")
    print("=" * 60)

    if args.dry_run:
        print("[DRY RUN MODE]")
    print()

    # Connect to databases
    print("Connecting to databases...")
    try:
        legacy_conn = psycopg2.connect(**LEGACY_DB)
        legacy_conn.autocommit = True
        print(f"  Legacy DB: {LEGACY_DB['dbname']} - OK")
    except Exception as e:
        print(f"  Legacy DB connection failed: {e}")
        return 1

    try:
        new_conn = psycopg2.connect(**NEW_DB)
        new_conn.autocommit = False
        print(f"  New DB: {NEW_DB['dbname']} - OK")
    except Exception as e:
        print(f"  New DB connection failed: {e}")
        legacy_conn.close()
        return 1

    print()

    # Run migration in a transaction
    try:
        if args.dry_run:
            _migrate_all(legacy_conn, new_conn, dry_run=True, skip_files=args.skip_files)
            new_conn.rollback()
        else:
            _migrate_all(legacy_conn, new_conn, dry_run=False, skip_files=args.skip_files)
            new_conn.commit()
    except Exception as e:
        print(f"\nMigration failed: {e}")
        new_conn.rollback()
        raise
    finally:
        legacy_conn.close()
        new_conn.close()

    print("\nMigration completed successfully!")
    return 0


def _migrate_all(legacy_conn, new_conn, dry_run: bool, skip_files: bool):
    """Run all migration steps."""
    cursor = new_conn.cursor()

    # Check current state
    cursor.execute("SELECT COUNT(*) as c FROM usuarios_area")
    areas_count = cursor.fetchone()[0]
    print(f"Current Areas in new DB: {areas_count}")

    cursor.execute("SELECT COUNT(*) as c FROM auth_user")
    users_count = cursor.fetchone()[0]
    print(f"Current Users in new DB: {users_count}")

    if areas_count == 0:
        print("\nERROR: No areas found. Please run seeds first:")
        print("  python manage.py seed_areas")
        print("  python manage.py seed_tipo_documento")
        raise Exception("Areas not seeded")

    # 1. Migrate users
    users_migrated = _migrate_users(legacy_conn, new_conn, dry_run)
    print(f"\n  Users migrated: {users_migrated}")

    # 2. Migrate asignaciones
    asignaciones_migrated = _migrate_asignaciones(legacy_conn, new_conn, dry_run)
    print(f"  Asignaciones migrated: {asignaciones_migrated}")

    # 3. Migrate expedientes
    exp_migrated = _migrate_expedientes(legacy_conn, new_conn, dry_run)
    print(f"  Expedientes migrated: {exp_migrated}")

    # 4. Migrar solicitudes
    sol_migrated = _migrate_solicitudes(legacy_conn, new_conn, dry_run)
    print(f"  Solicitudes migrated: {sol_migrated}")

    # 5. Migrate files
    if not skip_files:
        archivos_migrated = _migrate_archivos(legacy_conn, new_conn, dry_run)
        print(f"  Archivos migrated: {archivos_migrated}")
    else:
        print("  Files skipped (--skip-files)")

    cursor.close()


def _migrate_users(legacy_conn, new_conn, dry_run: bool) -> int:
    """Migrate 102 users."""
    cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT id, username, email, first_name, last_name, is_staff, is_active
        FROM auth_user ORDER BY id
    """)
    users = cursor.fetchall()
    cursor.close()

    new_cursor = new_conn.cursor()
    count = 0
    seen_emails = set()

    for row in users:
        email = row['email'] or ''
        username = row['username']

        # Handle duplicate email
        if email == 'secretaria@ciplima.org.pe':
            if email in seen_emails:
                email = 'secretaria-duplicado'
            seen_emails.add(email)

        if dry_run:
            print(f"    [DRY] User: {username}")
            count += 1
            continue

        # Check if user already exists
        new_cursor.execute("SELECT id FROM auth_user WHERE username = %s", (username,))
        if new_cursor.fetchone():
            continue

        # Create user with hashed password 'admin'
        # Django's PBKDF2 algorithm - we'll use a simple approach
        # For the migration, we just need the users to exist
        password_hash = 'pbkdf2_sha256$216000$salt$hash'  # Placeholder - will be reset

        try:
            new_cursor.execute("""
                INSERT INTO auth_user (password, last_login, is_superuser, username,
                    first_name, last_name, email, is_staff, is_active, date_joined)
                VALUES (%s, NULL, false, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                'admin',  # We'll set this properly
                username,
                row['first_name'] or '',
                row['last_name'] or '',
                email,
                row['is_staff'],
                row['is_active'],
            ))
            count += 1
        except Exception as e:
            print(f"    Warning: User {username}: {e}")

    new_cursor.close()
    return count


def _migrate_asignaciones(legacy_conn, new_conn, dry_run: bool) -> int:
    """Migrate AsignacionUsuario for adjuntados users."""
    cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT DISTINCT up.user_id, up.area_id, u.username, a.nombre as area_nombre
        FROM solicitudes_usuariosolicitudadjuntado ua
        JOIN auth_user u ON ua.usuario_id = u.id
        JOIN usuarios_perfilusuario up ON up.user_id = u.id
        JOIN usuarios_area a ON up.area_id = a.id
        WHERE up.area_id IS NOT NULL
    """)
    adjuntados = cursor.fetchall()
    cursor.close()

    new_cursor = new_conn.cursor()
    count = 0
    periodo_inicio = '2026-01-01'

    # Get or create cargo
    new_cursor.execute("SELECT id FROM usuarios_cargo WHERE nombre = 'Operador'")
    result = new_cursor.fetchone()
    if not result:
        new_cursor.execute("INSERT INTO usuarios_cargo (nombre, activo) VALUES ('Operador', true) RETURNING id")
        cargo_id = new_cursor.fetchone()[0]
    else:
        cargo_id = result[0]

    for row in adjuntados:
        # Find the user by username
        new_cursor.execute("SELECT id FROM auth_user WHERE username = %s", (row['username'],))
        user_result = new_cursor.fetchone()
        if not user_result:
            print(f"    Warning: User not found: {row['username']}")
            continue

        user_id = user_result[0]

        # Find the area by nombre
        new_cursor.execute("SELECT id FROM usuarios_area WHERE nombre = %s", (row['area_nombre'],))
        area_result = new_cursor.fetchone()
        if not area_result:
            print(f"    Warning: Area not found: {row['area_nombre']}")
            continue

        area_id = area_result[0]

        if dry_run:
            print(f"    [DRY] Asignacion: {row['username']} -> {row['area_nombre']}")
            count += 1
            continue

        # Check if asignacion already exists
        new_cursor.execute("""
            SELECT id FROM usuarios_asignacionusuario
            WHERE usuario_id = %s AND periodo_fin IS NULL
        """, (user_id,))
        if new_cursor.fetchone():
            continue

        try:
            new_cursor.execute("""
                INSERT INTO usuarios_asignacionusuario
                (id, area_id, cargo_id, usuario_id, periodo_inicio, periodo_fin, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NULL, NOW(), NOW())
            """, (uuid.uuid4(), area_id, cargo_id, user_id, periodo_inicio))
            count += 1
        except Exception as e:
            print(f"    Warning: Asignacion for {row['username']}: {e}")

    new_cursor.close()
    return count


def _migrate_expedientes(legacy_conn, new_conn, dry_run: bool) -> int:
    """Migrate expedientes preserving UUIDs."""
    cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT e.*, u.username as creado_por_username
        FROM expedientes_expediente e
        JOIN auth_user u ON e.creado_por_id = u.id
        ORDER BY e.fecha_creacion
    """)
    expedientes = cursor.fetchall()
    cursor.close()

    new_cursor = new_conn.cursor()
    count = 0
    numero_by_year = {}

    for row in expedientes:
        # Find the created_by user
        new_cursor.execute("SELECT id FROM auth_user WHERE username = %s", (row['creado_por_username'],))
        user_result = new_cursor.fetchone()
        if not user_result:
            new_cursor.execute("SELECT id FROM auth_user WHERE username = 'admin'")
            user_result = new_cursor.fetchone()
        if not user_result:
            print(f"    Warning: Creator not found: {row['creado_por_username']}")
            continue
        creado_por_id = user_result[0]

        # Map tipo_documento
        new_cursor.execute("SELECT id FROM tramites_tipo_documento WHERE nombre = %s", (row['tipo_documento'],))
        td_result = new_cursor.fetchone()
        if not td_result:
            print(f"    Warning: TipoDocumento not found: {row['tipo_documento']}")
            continue
        tipo_documento_id = td_result[0]

        # Map tipo_persona
        tipo_persona = row['tipo_persona'] or 'NATURAL'
        if tipo_persona not in ['NATURAL', 'JURIDICA', 'COLEGIADO']:
            tipo_persona = 'NATURAL'

        # Compute numero by year
        fecha_creacion = row['fecha_creacion']
        year = fecha_creacion.year
        if year not in numero_by_year:
            new_cursor.execute("""
                SELECT COUNT(*) FROM tramites_expediente
                WHERE EXTRACT(YEAR FROM fecha_registro) = %s
            """, (year,))
            numero_by_year[year] = new_cursor.fetchone()[0]
        numero_by_year[year] += 1
        numero = numero_by_year[year]

        if dry_run:
            print(f"    [DRY] Expediente: {row['id_publico']}")
            count += 1
            continue

        # Check if already exists
        new_cursor.execute("SELECT id FROM tramites_expediente WHERE id = %s", (row['id'],))
        if new_cursor.fetchone():
            continue

        try:
            new_cursor.execute("""
                INSERT INTO tramites_expediente
                (id, numero, tipo_persona, dni, ruc, cip, razon_social, nombres, apellidos,
                 correo, telefono, tipo_documento_id, numero_documento, numero_folios, asunto,
                 observaciones, fecha_registro, creado_por_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                row['id'],
                numero,
                tipo_persona,
                row['dni'] or '',
                row['ruc'] or '',
                row['cip'] or '',
                row['razon_social'] or '',
                row['nombres'] or '',
                row['apellidos'] or '',
                row['correo'] or '',
                row['telefono'] or '',
                tipo_documento_id,
                row['numero_documento'] or '',
                row['numero_folios'] or 0,
                row['asunto'] or '',
                row['observaciones'] or '',
                fecha_creacion,
                creado_por_id,
            ))
            count += 1
        except Exception as e:
            print(f"    Warning: Expediente {row['id']}: {e}")

    new_cursor.close()
    return count


def _migrate_solicitudes(legacy_conn, new_conn, dry_run: bool) -> int:
    """Migrate solicitudes with state mapping."""
    cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT s.*, u.username as creado_por_username, e.id as expediente_uuid
        FROM solicitudes_solicitud s
        JOIN auth_user u ON s.creado_por_id = u.id
        JOIN expedientes_expediente e ON s.expediente_id = e.id
        ORDER BY s.fecha_creacion
    """)
    solicitudes = cursor.fetchall()
    cursor.close()

    new_cursor = new_conn.cursor()
    count = 0

    for row in solicitudes:
        # Find the expediente
        new_cursor.execute("SELECT id FROM tramites_expediente WHERE id = %s", (row['expediente_uuid'],))
        exp_result = new_cursor.fetchone()
        if not exp_result:
            print(f"    Warning: Expediente not found: {row['expediente_uuid']}")
            continue
        expediente_id = exp_result[0]

        # Find created_by user
        new_cursor.execute("SELECT id FROM auth_user WHERE username = %s", (row['creado_por_username'],))
        user_result = new_cursor.fetchone()
        if not user_result:
            new_cursor.execute("SELECT id FROM auth_user WHERE username = 'admin'")
            user_result = new_cursor.fetchone()
        if not user_result:
            continue
        creado_por_id = user_result[0]

        # Map state
        legacy_state = row['estado']
        new_state = STATE_MAP.get(legacy_state, 'EN_TRAMITE')

        if dry_run:
            print(f"    [DRY] Solicitud: {row['id_publico']} {legacy_state}->{new_state}")
            count += 1
            continue

        # Check if already exists
        new_cursor.execute("SELECT id FROM tramites_solicitud WHERE id = %s", (row['id'],))
        if new_cursor.fetchone():
            continue

        try:
            new_cursor.execute("""
                INSERT INTO tramites_solicitud
                (id, expediente_id, estado, prioridad, fecha_registro, fecha_inicio_gestion,
                 fecha_limite, fecha_cierre, creado_por_id, observacion, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                row['id'],
                expediente_id,
                new_state,
                'MEDIA',
                row['fecha_creacion'],
                None,
                row['fecha_limite'],
                row['fecha_cierre'],
                creado_por_id,
                '',
            ))
            count += 1
        except Exception as e:
            print(f"    Warning: Solicitud {row['id']}: {e}")

    new_cursor.close()
    return count


def _migrate_archivos(legacy_conn, new_conn, dry_run: bool) -> int:
    """Migrate ExpedienteArchivos and SolicitudArchivos."""
    count = 0
    new_cursor = new_conn.cursor()

    # ExpedienteArchivos
    cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT ea.*, e.id as expediente_uuid, e.creado_por_id
        FROM expedientes_expedientearchivoanexo ea
        JOIN expedientes_expediente e ON ea.expediente_id = e.id
    """)
    exp_archivos = cursor.fetchall()
    cursor.close()

    for row in exp_archivos:
        new_cursor.execute("SELECT id FROM tramites_expediente WHERE id = %s", (row['expediente_uuid'],))
        exp_result = new_cursor.fetchone()
        if not exp_result:
            continue
        expediente_id = exp_result[0]

        if dry_run:
            print(f"    [DRY] ExpedienteArchivo: {row['archivo_anexo']}")
            count += 1
            continue

        # Check if already exists
        new_cursor.execute("SELECT id FROM tramites_expediente_archivo WHERE id = %s", (row['id'],))
        if new_cursor.fetchone():
            continue

        try:
            new_cursor.execute("""
                INSERT INTO tramites_expediente_archivo
                (id, expediente_id, tipo_archivo, archivo, nombre_original, descripcion,
                 creado_por_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                row['id'],
                expediente_id,
                'ANEXO',
                row['archivo_anexo'],
                row['nombre_original'] or 'anexo',
                row['descripcion'] or '',
                row['creado_por_id'],
            ))
            count += 1
        except Exception as e:
            print(f"    Warning: ExpedienteArchivo {row['id']}: {e}")

    # SolicitudArchivos (new table)
    cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
        SELECT sa.*, s.id as solicitud_uuid, s.creado_por_id
        FROM solicitudes_solicitudarchivoanexo sa
        JOIN solicitudes_solicitud s ON sa.solicitud_id = s.id
    """)
    sol_archivos = cursor.fetchall()
    cursor.close()

    for row in sol_archivos:
        new_cursor.execute("SELECT id FROM tramites_solicitud WHERE id = %s", (row['solicitud_uuid'],))
        sol_result = new_cursor.fetchone()
        if not sol_result:
            continue

        if dry_run:
            print(f"    [DRY] SolicitudArchivo: {row['archivo_anexo']}")
            count += 1
            continue

        # Check if already exists
        new_cursor.execute("SELECT id FROM tramites_solicitud_archivo WHERE id = %s", (row['id'],))
        if new_cursor.fetchone():
            continue

        try:
            new_cursor.execute("""
                INSERT INTO tramites_solicitud_archivo
                (id, solicitud_id, archivo, nombre_original, descripcion,
                 creado_por_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                row['id'],
                row['solicitud_uuid'],
                row['archivo_anexo'],
                row['archivo_anexo'].split('/')[-1] if '/' in row['archivo_anexo'] else row['archivo_anexo'],
                row['descripcion'] or '',
                row['creado_por_id'],
            ))
            count += 1
        except Exception as e:
            print(f"    Warning: SolicitudArchivo {row['id']}: {e}")

    new_cursor.close()
    return count


if __name__ == '__main__':
    sys.exit(main())
