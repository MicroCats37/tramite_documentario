"""
ETL command to migrate data from legacy mesa_partes database.

Usage:
    python manage.py migracion_datos_legacy
    python manage.py migracion_datos_legacy --files-backend local
    python manage.py migracion_datos_legacy --files-backend saaa-dry --dry-run
    python manage.py migracion_datos_legacy --since 2026-10-14T00:00:00+00:00
    python manage.py migracion_datos_legacy --expediente-id UUID --files-backend saaa

Environment variables:
    LEGACY_DB_HOST, LEGACY_DB_PORT, LEGACY_DB_NAME, LEGACY_DB_USER, LEGACY_DB_PASSWORD
    LEGACY_MEDIA_ROOT  (default: data-new/media_local relative to backend root)
    SAAA_USE_FAKE     (default: true in DEBUG mode)
"""

import hashlib
import json
import mimetypes
import os
import uuid
from datetime import date, datetime, timedelta, timezone as datetime_timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from modules.usuarios.domain.models import Area, Usuario, Cargo, AsignacionUsuario
from modules.asignaciones.domain.models import (
    SolicitudAsignacion, SolicitudAsignacionPeriodo, SolicitudAsignacionUsuario,
)
from modules.asignaciones.domain.constants import (
    EstadoPeriodo, TipoCierre, TipoParticipacion, TipoRespuesta,
)
from modules.conversaciones.domain.constants import TipoMensaje
from modules.conversaciones.domain.models import Conversacion, Mensaje, MensajeArchivoAdjunto, SolicitudConversacion
from modules.tramites.domain.models import (
    Archivo, Expediente, Solicitud, TipoDocumento,
    ExpedienteArchivo, SolicitudEstadoHistorial, SolicitudRespuesta,
)
from modules.tramites.domain.constants import EstadoSolicitud, Prioridad, TipoPersona, TipoArchivo
from modules.tramites.domain.models.solicitud_historial import OrigenCambio
from modules.tramites.infrastructure.saaa_client import RealSaaaClient


# ── Legacy database connection ─────────────────────────────────────────────────

LEGACY_DB = {
    'host': os.environ.get('LEGACY_DB_HOST', 'localhost'),
    'port': int(os.environ.get('LEGACY_DB_PORT', '15433')),
    'dbname': os.environ.get('LEGACY_DB_NAME', 'mesa_partes_db'),
    'user': os.environ.get('LEGACY_DB_USER', 'postgres'),
    'password': os.environ.get('LEGACY_DB_PASSWORD', 'postgres'),
}

LEGACY_ID_NAMESPACE = uuid.UUID("a0839a91-2fc5-4b12-a582-7f2a9d1fda9a")


def _get_legacy_media_root() -> Path:
    """Resolve LEGACY_MEDIA_ROOT, defaulting to data-new/media_local at project root."""
    # Walk up from this file to find project root.
    # __file__ is backend/modules/migracion/management/commands/migracion_datos_legacy.py
    # 6 parents up: commands -> management -> migracion -> modules -> backend -> project root
    project_root = Path(__file__).resolve().parents[5]
    default_root = project_root / "data-new" / "media_local"
    return Path(os.environ.get("LEGACY_MEDIA_ROOT", str(default_root)))


class Command(BaseCommand):
    help = "Migrate data from legacy mesa_partes database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate without writing to the database.",
        )
        parser.add_argument(
            "--skip-files",
            action="store_true",
            help="Skip file migration.",
        )
        parser.add_argument(
            "--files-backend",
            choices=["local", "saaa", "saaa-dry"],
            default="local",
            help=(
                "File storage backend for migrated files. "
                "'local' (default): store the legacy path as storage_reference. "
                "'saaa': upload each file to the configured SAAA service. "
                "'saaa-dry': simulate SAAA upload without actual upload (dry-run only for SAAA)."
            ),
        )
        parser.add_argument(
            "--analyze-only",
            action="store_true",
            help="Analyze legacy files and print report without migrating anything.",
        )
        parser.add_argument(
            "--since",
            metavar="ISO_8601_DATETIME",
            help=(
                "Incremental mode cutoff. Strict ISO 8601 datetime with an explicit "
                "UTC offset, for example 2026-10-14T00:00:00+00:00. "
                "Only creates data sourced at or after this instant; existing "
                "destination records are never updated."
            ),
        )
        parser.add_argument(
            "--expediente-id",
            type=uuid.UUID,
            help=(
                "Migrate only this legacy expediente UUID and its dependent records. "
                "When supplied, users and standalone assignments are not migrated."
            ),
        )

    def handle(self, *args, **options) -> None:
        dry_run: bool = options["dry_run"]
        skip_files: bool = options["skip_files"]
        files_backend: str = options["files_backend"]
        analyze_only: bool = options["analyze_only"]
        since = self._parse_since(options.get("since"))
        expediente_id: uuid.UUID | None = options.get("expediente_id")

        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write(self.style.WARNING("MIGRATION: migracion_datos_legacy"))
        self.stdout.write(self.style.WARNING("=" * 60))

        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY RUN MODE]"))
        if since:
            self.stdout.write(self.style.WARNING(
                f"[INCREMENTAL MODE] Source cutoff (inclusive): {since.isoformat()}"
            ))
        if expediente_id:
            self.stdout.write(self.style.WARNING(
                f"[EXPEDIENTE SCOPE] Legacy expediente: {expediente_id}"
            ))

        # Resolve media root
        legacy_media_root = _get_legacy_media_root()
        self.stdout.write(self.style.SUCCESS(f"Legacy media root: {legacy_media_root}"))
        if not legacy_media_root.exists():
            self.stdout.write(self.style.ERROR(f"Legacy media root does not exist: {legacy_media_root}"))
            self.stdout.write(self.style.WARNING("Set LEGACY_MEDIA_ROOT env var to point to the legacy media directory."))
            if not analyze_only:
                self.stdout.write(self.style.ERROR("Cannot proceed without media root. Use --analyze-only to just analyze."))
                return

        # Connect to legacy database
        try:
            legacy_conn = psycopg2.connect(**LEGACY_DB)
            legacy_conn.autocommit = True
            self.stdout.write(self.style.SUCCESS(f"Connected to legacy DB: {LEGACY_DB['dbname']}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to connect to legacy DB: {e}"))
            return

        if analyze_only:
            self.stdout.write(self.style.WARNING("\n[ANALYZE MODE]"))
            self._analyze_legacy_files(legacy_conn, legacy_media_root)
            legacy_conn.close()
            self.stdout.write(self.style.SUCCESS("\nAnalysis complete."))
            return

        # Run migration in atomic transaction
        with transaction.atomic():
            if dry_run:
                self.stdout.write(self.style.WARNING("[DRY RUN] Would migrate:"))

            # A selected expediente uses destination users already present. Do not
            # touch unrelated users or assignments during a scoped import.
            users_count = 0 if expediente_id else self._migrate_users(legacy_conn, dry_run, since)
            self.stdout.write(self.style.SUCCESS(f"  Users migrated: {users_count}"))

            # 2. Migrate areas (from seeds, already loaded)
            areas_count = Area.objects.count()
            self.stdout.write(self.style.SUCCESS(f"  Areas (from seeds): {areas_count}"))

            # 3. Migrate TipoDocumento (from seeds, already loaded)
            td_count = TipoDocumento.objects.count()
            self.stdout.write(self.style.SUCCESS(f"  TipoDocumento (from seeds): {td_count}"))

            # 4. Migrate asignaciones (AsignacionUsuario for adjuntados)
            asignaciones_count = 0 if expediente_id else self._migrate_asignaciones(legacy_conn, dry_run, since)
            self.stdout.write(self.style.SUCCESS(f"  Asignaciones migrated: {asignaciones_count}"))

            # 5. Migrate expedientes
            exp_count = self._migrate_expedientes(legacy_conn, dry_run, since, expediente_id)
            self.stdout.write(self.style.SUCCESS(f"  Expedientes migrated: {exp_count}"))

            # 6. Migrar solicitudes
            sol_count = self._migrate_solicitudes(legacy_conn, dry_run, since, expediente_id)
            self.stdout.write(self.style.SUCCESS(f"  Solicitudes migrated: {sol_count}"))

            # 7. Migrar historial de estados y respuestas finales
            historial_count = self._migrate_historial_estados(legacy_conn, dry_run, since, expediente_id)
            self.stdout.write(self.style.SUCCESS(f"  Historial estados migrated: {historial_count}"))

            respuestas_count = self._migrate_respuestas_finales(legacy_conn, dry_run, since, expediente_id)
            self.stdout.write(self.style.SUCCESS(f"  Respuestas finales migrated: {respuestas_count}"))

            # 8. Migrate files
            if not skip_files:
                self.stdout.write(self.style.SUCCESS(f"  File backend: {files_backend}"))
                # 8a. Expediente principal files
                princ_count = self._migrate_expediente_principal_archivos(
                    legacy_conn, dry_run, files_backend, legacy_media_root, since, expediente_id
                )
                self.stdout.write(self.style.SUCCESS(f"  ExpedientePrincipal archivos migrated: {princ_count}"))
                # 8b. Expediente anexo files (existing method, enhanced)
                anexos_count = self._migrate_expediente_anexo_archivos(
                    legacy_conn, dry_run, files_backend, legacy_media_root, since, expediente_id
                )
                self.stdout.write(self.style.SUCCESS(f"  ExpedienteAnexo archivos migrated: {anexos_count}"))
                # 8c. Comment messages
                msg_count = self._migrate_comentarios_to_mensajes(
                    legacy_conn, dry_run, files_backend, legacy_media_root, since, expediente_id
                )
                self.stdout.write(self.style.SUCCESS(f"  Comentarios -> Mensajes migrated: {msg_count}"))
                # 8d. Solicitud anexo files -> attach to conversation
                sol_arch_count = self._migrate_solicitud_archivo_anexos(
                    legacy_conn, dry_run, files_backend, legacy_media_root, since, expediente_id
                )
                self.stdout.write(self.style.SUCCESS(f"  SolicitudArchivoAnexo migrated: {sol_arch_count}"))
            else:
                self.stdout.write(self.style.WARNING("  Skipping files (--skip-files)"))

            # 9. Backfill empty Conversacion + SolicitudConversacion for
            #    every Solicitud that does not yet have one. The legacy
            #    system did not have conversaciones; the new flow creates
            #    one on every solicitud creation, so we mirror that here.
            conv_count = self._backfill_conversaciones(
                dry_run=dry_run,
                since=since,
                expediente_id=expediente_id,
            )
            self.stdout.write(self.style.SUCCESS(
                f"  Conversaciones backfilled: {conv_count}"
            ))

        legacy_conn.close()

        self.stdout.write(self.style.SUCCESS("\nMigration completed successfully!"))

    @staticmethod
    def _parse_since(value: str | None) -> datetime | None:
        """Return an aware ISO 8601 cutoff, or reject ambiguous local datetimes."""
        if value is None:
            return None
        if "T" not in value:
            raise CommandError("--since must use ISO 8601 date-time format with 'T'.")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise CommandError("--since must be a valid ISO 8601 date-time.") from exc
        if not timezone.is_aware(parsed):
            raise CommandError("--since must include an explicit UTC offset, for example +00:00.")
        return parsed.astimezone(datetime_timezone.utc)

    @staticmethod
    def _legacy_uuid(kind: str, source_id: object) -> uuid.UUID:
        """Create a stable destination UUID from an immutable legacy row identity."""
        return uuid.uuid5(LEGACY_ID_NAMESPACE, f"{kind}:{source_id}")

    def _migrate_users(self, legacy_conn, dry_run: bool, since: datetime | None = None) -> int:
        """Migrate 102 users from legacy auth_user table."""
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT id, username, email, first_name, last_name, is_staff, is_active
            FROM auth_user
        """
        params = []
        if since:
            query += " WHERE date_joined >= %s"
            params.append(since)
        query += " ORDER BY id"
        cursor.execute(query, params)
        users = cursor.fetchall()
        cursor.close()

        count = 0
        seen_emails = set()

        for row in users:
            email = row['email'] or ''
            username = row['username']

            # Handle duplicate email: secretaria@ciplima.org.pe -> secretaria-duplicado
            if email:
                if email in seen_emails:
                    email = 'secretaria-duplicado'
                else:
                    seen_emails.add(email)

            if dry_run:
                self.stdout.write(f"    [DRY] User: {username}")
                count += 1
                continue

            # Get or create user (skip if exists)
            user, created = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'nombres': row['first_name'] or '',
                    'apellidos': row['last_name'] or '',
                    'is_staff': row['is_staff'],
                    'is_active': row['is_active'],
                }
            )
            if created:
                user.set_password('admin')  # Default password: admin
                user.save(update_fields=['password'])
                count += 1

        return count

    def _migrate_asignaciones(self, legacy_conn, dry_run: bool, since: datetime | None = None) -> int:
        """
        Migrate AsignacionUsuario from the union of:
         - usuario_asignado_id in solicitudes_solicitud (area principal)
         - usuario_id in solicitudes_usuariosolicitudadjuntado (adjuntados)
        Each user's area comes from their perfil (usuarios_perfilusuario.area_id).
        """
        # Union of assigned users (area principal) + adjuntados, with their profile area
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT DISTINCT u.id AS user_id, u.username, a.nombre AS area_nombre
            FROM (
                SELECT DISTINCT s.usuario_asignado_id AS uid
                FROM solicitudes_solicitud s
                {solicitud_cutoff}
                UNION
                SELECT DISTINCT ua.usuario_id
                FROM solicitudes_usuariosolicitudadjuntado ua
                JOIN solicitudes_solicitud s ON s.id = ua.solicitud_id
                {adjunto_cutoff}
            ) x
            JOIN auth_user u ON u.id = x.uid
            JOIN usuarios_perfilusuario up ON up.user_id = u.id
            JOIN usuarios_area a ON up.area_id = a.id
            WHERE up.area_id IS NOT NULL
            ORDER BY u.username
        """
        params = []
        if since:
            query = query.format(
                solicitud_cutoff="WHERE s.fecha_creacion >= %s",
                adjunto_cutoff="WHERE s.fecha_creacion >= %s",
            )
            params = [since, since]
        else:
            query = query.format(solicitud_cutoff="", adjunto_cutoff="")
        cursor.execute(query, params)
        adjuntados = cursor.fetchall()
        cursor.close()

        # Get or create a default Cargo
        cargo, _ = Cargo.objects.get_or_create(
            nombre='Operador',
            defaults={'activo': True}
        )

        count = 0
        periodo_inicio = date(2026, 1, 1)

        for row in adjuntados:
            try:
                usuario = Usuario.objects.get(username=row['username'])
            except Usuario.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"    User not found: {row['username']}"))
                continue

            # Find the area by nombre in the new system
            try:
                area = Area.objects.get(nombre=row['area_nombre'])
            except Area.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"    Area not found: {row['area_nombre']}"))
                continue

            if dry_run:
                self.stdout.write(f"    [DRY] Asignacion: {usuario.username} -> {area.nombre}")
                count += 1
                continue

            # Create AsignacionUsuario
            asignacion, created = AsignacionUsuario.objects.get_or_create(
                usuario=usuario,
                defaults={
                    'area': area,
                    'cargo': cargo,
                    'periodo_inicio': periodo_inicio,
                    'periodo_fin': None,
                }
            )
            if created:
                count += 1

        return count

    def _migrate_expedientes(
        self, legacy_conn, dry_run: bool, since: datetime | None = None,
        expediente_id: uuid.UUID | None = None,
    ) -> int:
        """Migrate 487 expedientes, preserving legacy UUIDs."""
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT e.*, u.username as creado_por_username
            FROM expedientes_expediente e
            JOIN auth_user u ON e.creado_por_id = u.id
        """
        params = []
        if expediente_id:
            query += " WHERE e.id = %s"
            params.append(str(expediente_id))
        elif since:
            query += " WHERE e.fecha_creacion >= %s"
            params.append(since)
        query += " ORDER BY e.fecha_creacion"
        cursor.execute(query, params)
        expedientes = cursor.fetchall()
        cursor.close()

        count = 0
        # Track numero per year
        numero_by_year = {}

        for row in expedientes:
            try:
                creado_por = Usuario.objects.get(username=row['creado_por_username'])
            except Usuario.DoesNotExist:
                # Try admin as fallback
                try:
                    creado_por = Usuario.objects.get(username='admin')
                except Usuario.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"    Creator not found: {row['creado_por_username']}"))
                    continue

            # Map tipo_documento
            tipo_doc_nombre = row['tipo_documento']
            tipo_documento, tipo_doc_created = TipoDocumento.objects.get_or_create(
                nombre=tipo_doc_nombre,
                defaults={
                    "descripcion": tipo_doc_nombre.replace("_", " ").title(),
                },
            )
            if tipo_doc_created:
                self.stdout.write(self.style.WARNING(f"    TipoDocumento legacy created: {tipo_doc_nombre}"))

            # Map tipo_persona
            tipo_persona = row['tipo_persona'] or 'NATURAL'
            if tipo_persona not in [choice[0] for choice in TipoPersona.choices]:
                tipo_persona = 'NATURAL'

            # Compute numero by year
            fecha_creacion = row['fecha_creacion']
            year = fecha_creacion.year
            if year not in numero_by_year:
                # Get the max numero for this year from already migrated or existing
                existing_max = Expediente.objects.filter(
                    fecha_registro__year=year
                ).count()
                numero_by_year[year] = existing_max
            numero_by_year[year] += 1
            numero = numero_by_year[year]

            if dry_run:
                self.stdout.write(f"    [DRY] Expediente: {row['id_publico']}")
                count += 1
                continue

            # Check if already exists (by legacy UUID)
            if Expediente.objects.filter(id=row['id']).exists():
                continue

            expediente = Expediente.objects.create(
                id=row['id'],  # Preserve legacy UUID
                numero=numero,
                tipo_persona=tipo_persona,
                dni=row['dni'] or '',
                ruc=row['ruc'] or '',
                cip=row['cip'] or '',
                razon_social=row['razon_social'] or '',
                nombres=row['nombres'] or '',
                apellidos=row['apellidos'] or '',
                correo=row['correo'] or '',
                telefono=row['telefono'] or '',
                tipo_documento=tipo_documento,
                numero_documento=row['numero_documento'] or '',
                numero_folios=row['numero_folios'] or 0,
                asunto=row['asunto'] or '',
                observaciones=row['observaciones'] or '',
                fecha_registro=fecha_creacion,
                creado_por=creado_por,
            )
            count += 1

        return count

    def _migrate_solicitudes(
        self, legacy_conn, dry_run: bool, since: datetime | None = None,
        expediente_id: uuid.UUID | None = None,
    ) -> int:
        """Migrate 480 solicitudes, mapping states and preserving UUIDs."""
        # Map legacy states -> new states
        STATE_MAP = {
            'CERRADO': EstadoSolicitud.FINALIZADA,
            'ENVIADO_A_AREA': EstadoSolicitud.EN_TRAMITE,
            'EN_GESTION_MP': EstadoSolicitud.EN_GESTION,
            'REENVIO_MP': EstadoSolicitud.EN_TRAMITE,
        }

        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT s.*,
                   u.username as creado_por_username,
                   ua.username as asignado_username,
                   a.nombre as asignado_area_nombre,
                   e.id as expediente_uuid
            FROM solicitudes_solicitud s
            JOIN auth_user u ON s.creado_por_id = u.id
            JOIN auth_user ua ON s.usuario_asignado_id = ua.id
            LEFT JOIN usuarios_perfilusuario up ON up.user_id = ua.id
            LEFT JOIN usuarios_area a ON up.area_id = a.id
            JOIN expedientes_expediente e ON s.expediente_id = e.id
        """
        params = []
        if expediente_id:
            query += " WHERE e.id = %s"
            params.append(str(expediente_id))
        elif since:
            # A newly created expediente brings all its dependent solicitudes,
            # even if their timestamps predate the chosen cutoff.
            query += " WHERE s.fecha_creacion >= %s OR e.fecha_creacion >= %s"
            params = [since, since]
        query += " ORDER BY s.fecha_creacion"
        cursor.execute(query, params)
        solicitudes = cursor.fetchall()
        cursor.close()

        count = 0

        for row in solicitudes:
            # Find the expediente by legacy UUID
            try:
                expediente = Expediente.objects.get(id=row['expediente_uuid'])
            except Expediente.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"    Expediente not found: {row['expediente_uuid']}"))
                continue

            # Map state
            legacy_state = row['estado']
            new_state = STATE_MAP.get(legacy_state, EstadoSolicitud.EN_TRAMITE)

            # Get created_by user
            try:
                creado_por = Usuario.objects.get(username=row['creado_por_username'])
            except Usuario.DoesNotExist:
                try:
                    creado_por = Usuario.objects.get(username='admin')
                except Usuario.DoesNotExist:
                    continue

            if dry_run:
                self.stdout.write(f"    [DRY] Solicitud: {row['id_publico']} {legacy_state}->{new_state}")
                count += 1
                continue

            # Check if already exists
            if Solicitud.objects.filter(id=row['id']).exists():
                continue

            solicitud = Solicitud.objects.create(
                id=row['id'],  # Preserve legacy UUID
                expediente=expediente,
                estado=new_state,
                prioridad=Prioridad.MEDIA,
                fecha_registro=row['fecha_creacion'],
                fecha_inicio_gestion=row['fecha_creacion'],
                fecha_limite=row['fecha_limite'],
                fecha_cierre=row['fecha_cierre'],
                creado_por=creado_por,
                observacion='',
            )

            # Build assignment chain: SolicitudAsignacion -> Periodo -> Usuario
            # using the legacy usuario_asignado_id (area principal) and its area.
            asignado = None
            if row.get('asignado_username'):
                try:
                    asignado = Usuario.objects.get(username=row['asignado_username'])
                except Usuario.DoesNotExist:
                    asignado = None

            area_principal = None
            if row.get('asignado_area_nombre'):
                try:
                    area_principal = Area.objects.get(nombre=row['asignado_area_nombre'])
                except Area.DoesNotExist:
                    area_principal = None

            if asignado and area_principal:
                fecha_inicio = row['fecha_creacion']

                asignacion, _ = SolicitudAsignacion.objects.get_or_create(
                    solicitud=solicitud,
                    area=area_principal,
                    defaults={
                        'fecha_incorporacion': fecha_inicio,
                        'incorporado_por': asignado,
                        'observacion': 'Migrado desde sistema legacy',
                    },
                )

                # Periodo del ciclo 1: cerrado si la solicitud finalizó, abierto en otro caso
                estado_periodo = (
                    EstadoPeriodo.CERRADO
                    if new_state == EstadoSolicitud.FINALIZADA
                    else EstadoPeriodo.EN_GESTION
                    if new_state == EstadoSolicitud.EN_GESTION
                    else EstadoPeriodo.PENDIENTE
                )

                periodo, _ = SolicitudAsignacionPeriodo.objects.get_or_create(
                    asignacion=asignacion,
                    numero_ciclo=1,
                    defaults={
                        'tipo_participacion': TipoParticipacion.PRINCIPAL,
                        'estado': estado_periodo,
                        'fecha_inicio': fecha_inicio,
                        'fecha_fin': (
                            row['fecha_cierre']
                            if new_state == EstadoSolicitud.FINALIZADA
                            else None
                        ),
                        'tipo_cierre': (
                            TipoCierre.FINALIZADO
                            if new_state == EstadoSolicitud.FINALIZADA
                            else None
                        ),
                        'iniciado_por': asignado,
                    },
                )

                SolicitudAsignacionUsuario.objects.get_or_create(
                    periodo=periodo,
                    usuario=asignado,
                    defaults={
                        'rol': 'Responsable',
                        'fecha_inicio': fecha_inicio,
                        'fecha_fin': (
                            row['fecha_cierre']
                            if new_state == EstadoSolicitud.FINALIZADA
                            else None
                        ),
                        'asignado_por': asignado,
                    },
                )

            count += 1

        return count

    def _legacy_user(self, legacy_conn, legacy_user_id: int | None) -> Usuario | None:
        """Resolve legacy auth_user.id to current Usuario by username."""
        if legacy_user_id is None:
            return None

        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT username FROM auth_user WHERE id = %s", (legacy_user_id,))
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return None

        try:
            return Usuario.objects.get(username=row["username"])
        except Usuario.DoesNotExist:
            return None

    def _map_legacy_estado(self, estado: str, finalizado: bool) -> str:
        if estado == "CERRADO":
            return EstadoSolicitud.FINALIZADA if finalizado else EstadoSolicitud.EN_GESTION
        if estado == "ENVIADO_A_AREA":
            return EstadoSolicitud.EN_TRAMITE
        if estado == "EN_GESTION_MP":
            return EstadoSolicitud.EN_GESTION
        if estado == "REENVIO_MP":
            return EstadoSolicitud.EN_TRAMITE
        return EstadoSolicitud.EN_TRAMITE

    def _migrate_historial_estados(
        self, legacy_conn, dry_run: bool, since: datetime | None = None,
        expediente_id: uuid.UUID | None = None,
    ) -> int:
        """Migrate legacy django-simple-history rows into SolicitudEstadoHistorial."""
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT h.id AS solicitud_id,
                   h.estado,
                   h.finalizado,
                   h.history_id,
                   h.history_date,
                   h.history_type,
                   h.history_user_id,
                   h.creado_por_id,
                   s.creado_por_id AS solicitud_creado_por_id,
                   s.fecha_creacion AS solicitud_fecha_creacion
            FROM solicitudes_historicalsolicitud h
            JOIN solicitudes_solicitud s ON s.id = h.id
            JOIN expedientes_expediente e ON s.expediente_id = e.id
        """
        params = []
        if expediente_id:
            query += " WHERE e.id = %s"
            params.append(str(expediente_id))
        elif since:
            # Fetch the full chain only for solicitudes affected by the cutoff so
            # appended transitions retain their true previous state.
            query += """ WHERE s.fecha_creacion >= %s OR EXISTS (
                SELECT 1 FROM solicitudes_historicalsolicitud changed
                WHERE changed.id = s.id AND changed.history_date >= %s
            )"""
            params = [since, since]
        query += " ORDER BY h.id, h.history_date, h.history_id"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()

        grouped: dict[str, list[dict]] = {}
        for row in rows:
            grouped.setdefault(str(row["solicitud_id"]), []).append(row)

        count = 0
        for solicitud_id, history_rows in grouped.items():
            try:
                solicitud = Solicitud.objects.get(id=solicitud_id)
            except Solicitud.DoesNotExist:
                continue

            # Preserve the full-migration behavior for an existing destination.
            # Incremental mode below appends only post-cutoff source transitions.
            if not since and SolicitudEstadoHistorial.objects.filter(solicitud=solicitud).exists():
                continue

            first = history_rows[0]
            creado_por = self._legacy_user(
                legacy_conn,
                first.get("solicitud_creado_por_id") or first.get("creado_por_id"),
            ) or solicitud.creado_por

            if not SolicitudEstadoHistorial.objects.filter(solicitud=solicitud).exists():
                artificial_fecha = first["history_date"] - timedelta(hours=2)
                initial_id = self._legacy_uuid("solicitud_historial_inicial", solicitud_id)
                if dry_run:
                    count += 1
                else:
                    SolicitudEstadoHistorial.objects.create(
                        id=initial_id,
                        solicitud=solicitud,
                        estado_anterior=None,
                        estado_nuevo=EstadoSolicitud.REGISTRADA,
                        fecha_cambio=artificial_fecha,
                        cambiado_por=creado_por,
                        motivo="Estado inicial inferido para migración desde sistema legacy",
                        observacion=None,
                        origen=OrigenCambio.CREACION,
                    )
                    count += 1

            previous_estado = EstadoSolicitud.REGISTRADA
            for row in history_rows:
                mapped_estado = self._map_legacy_estado(row["estado"], row["finalizado"])
                if mapped_estado == previous_estado:
                    continue

                if since and row["solicitud_fecha_creacion"] < since and row["history_date"] < since:
                    previous_estado = mapped_estado
                    continue

                history_id = self._legacy_uuid("solicitud_historial", row["history_id"])
                if SolicitudEstadoHistorial.objects.filter(id=history_id).exists():
                    previous_estado = mapped_estado
                    continue

                cambiado_por = (
                    self._legacy_user(legacy_conn, row.get("history_user_id"))
                    or creado_por
                )
                origen = (
                    OrigenCambio.CIERRE
                    if mapped_estado == EstadoSolicitud.FINALIZADA
                    else OrigenCambio.CAMBIO_ESTADO
                )
                if dry_run:
                    count += 1
                else:
                    SolicitudEstadoHistorial.objects.create(
                        id=history_id,
                        solicitud=solicitud,
                        estado_anterior=previous_estado,
                        estado_nuevo=mapped_estado,
                        fecha_cambio=row["history_date"],
                        cambiado_por=cambiado_por,
                        motivo=f"Migrado desde historial legacy #{row['history_id']}",
                        observacion=None,
                        origen=origen,
                    )
                    count += 1
                previous_estado = mapped_estado

        return count

    def _migrate_respuestas_finales(
        self, legacy_conn, dry_run: bool, since: datetime | None = None,
        expediente_id: uuid.UUID | None = None,
    ) -> int:
        """Create final CONFORMIDAD responses for truly finalized legacy solicitudes."""
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT s.id,
                   s.fecha_cierre,
                   s.modificado_por_id,
                   s.usuario_asignado_id
            FROM solicitudes_solicitud s
            JOIN expedientes_expediente e ON s.expediente_id = e.id
            WHERE s.estado = 'CERRADO' AND s.finalizado = true
        """
        params = []
        if expediente_id:
            query += " AND e.id = %s"
            params.append(str(expediente_id))
        elif since:
            query += " AND (s.fecha_creacion >= %s OR s.fecha_cierre >= %s)"
            params = [since, since]
        query += " ORDER BY s.fecha_cierre"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()

        count = 0
        for row in rows:
            try:
                solicitud = Solicitud.objects.get(id=row["id"])
            except Solicitud.DoesNotExist:
                continue

            if SolicitudRespuesta.objects.filter(solicitud=solicitud, es_final=True).exists():
                continue

            emitido_por = (
                self._legacy_user(legacy_conn, row.get("modificado_por_id"))
                or self._legacy_user(legacy_conn, row.get("usuario_asignado_id"))
                or solicitud.creado_por
            )

            periodo = (
                SolicitudAsignacionPeriodo.objects
                .filter(asignacion__solicitud=solicitud)
                .select_related("asignacion__area")
                .order_by("-fecha_inicio")
                .first()
            )
            if periodo is None:
                continue
            area = periodo.asignacion.area
            fecha = row["fecha_cierre"] or solicitud.fecha_cierre or solicitud.fecha_registro

            if dry_run:
                count += 1
                continue

            puente = SolicitudConversacion.objects.filter(
                solicitud=solicitud
            ).select_related("conversacion").first()
            if puente:
                conversacion = puente.conversacion
            else:
                conversacion = Conversacion.objects.create(
                    titulo=f"Conversación - {solicitud.expediente.id_publico}",
                    creada_por=solicitud.creado_por,
                    fecha_inicio=solicitud.fecha_registro,
                    fecha_cierre=fecha,
                    cerrado_por=emitido_por,
                )
                SolicitudConversacion.objects.create(
                    solicitud=solicitud,
                    conversacion=conversacion,
                )
            mensaje = Mensaje.objects.create(
                conversacion=conversacion,
                autor_usuario=None,
                contenido="Trámite cerrado conforme en sistema legacy",
                tipo=TipoMensaje.SISTEMA,
                fecha_envio=fecha,
            )
            respuesta = SolicitudRespuesta.objects.create(
                solicitud=solicitud,
                conversacion=conversacion,
                mensaje=mensaje,
                area=area,
                periodo=periodo,
                tipo_respuesta=TipoRespuesta.CONFORMIDAD,
                contenido="Trámite cerrado conforme en sistema legacy",
                es_final=True,
                emitido_por=emitido_por,
            )
            respuesta.fecha_emision = fecha
            respuesta.save(update_fields=["fecha_emision", "updated_at"])
            count += 1

        return count

    # ── File analysis helpers ─────────────────────────────────────────────────────

    def _resolve_legacy_file(self, legacy_path: str, media_root: Path) -> Path | None:
        """
        Resolve a legacy file path to a physical file under media_root.

        Handles both absolute-looking paths (starting with /) and relative paths.
        Returns None if the file does not exist.
        """
        if not legacy_path:
            return None
        # Strip leading slash for Path() — treat as relative within media_root
        clean = legacy_path.lstrip("/")
        full_path = media_root / clean
        if full_path.exists() and full_path.is_file():
            return full_path
        return None

    def _compute_file_metadata(self, local_path: Path) -> dict:
        """
        Compute metadata for a local file: size, mime_type, sha256.
        """
        size = local_path.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(local_path))
        sha256_hash = hashlib.sha256()
        with open(local_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256_hash.update(chunk)
        return {
            "size": size,
            "mime_type": mime_type,
            "sha256": sha256_hash.hexdigest(),
        }

    def _get_or_create_archivo(
        self,
        storage_backend: str,
        storage_reference: str,
        nombre_original: str | None,
        extension: str | None,
        mime_type: str | None,
        tamano_bytes: int | None,
        sha256: str | None,
        storage_metadata: dict,
        subido_por: Usuario | None,
        dry_run: bool,
        physical_path: Path | None = None,
    ) -> tuple[Archivo | None, bool]:
        """
        Get or create an Archivo record idempotently.

        Idempotency is based on storage_backend + storage_reference.
        If the record already exists, returns (existing, False).
        If created, returns (new, True).

        In dry-run mode, returns (None, True) for new records.

        When storage_backend == "saaa", a real upload is performed against
        the configured SAAA service using physical_path content; the returned
        archivo_id becomes the storage_reference and the configured SAAA_APP_ID
        becomes the storage_namespace.
        """
        if not storage_reference and storage_backend != "saaa":
            return None, False

        # For SAAA we need a real upload before we can know the archivo_id.
        # We use a per-call cache to dedupe uploads when many legacy rows
        # point to the same physical file (by SHA-256).
        if storage_backend == "saaa":
            if not physical_path or not physical_path.exists():
                self.stdout.write(self.style.WARNING(
                    f"    [SAAA SKIP] Physical file missing: {physical_path}"
                ))
                return None, False

            file_meta = self._compute_file_metadata(physical_path)
            cache_key = f"saaa::{file_meta['sha256']}::{nombre_original}"
            if not hasattr(self, "_saaa_upload_cache"):
                self._saaa_upload_cache = {}

            if cache_key in self._saaa_upload_cache:
                cached = self._saaa_upload_cache[cache_key]
                if dry_run:
                    return None, True
                existing = Archivo.objects.filter(
                    storage_backend="saaa",
                    storage_reference=cached["archivo_id"],
                ).select_related("subido_por").first()
                if existing:
                    return existing, False
                archivo = Archivo(
                    storage_backend="saaa",
                    storage_reference=cached["archivo_id"],
                    storage_namespace=cached["app_id"],
                    nombre_original=nombre_original,
                    extension=extension or cached.get("extension"),
                    mime_type=mime_type or file_meta["mime_type"],
                    tamano_bytes=tamano_bytes or file_meta["size"],
                    checksum_sha256=sha256 or file_meta["sha256"],
                    storage_metadata={**(storage_metadata or {}), "path_relativo": cached["path_relativo"]},
                    subido_por=subido_por,
                )
                archivo.save()
                return archivo, True

            if dry_run:
                return None, True

            with open(physical_path, "rb") as fh:
                file_content = fh.read()

            saaa_client = RealSaaaClient()
            upload = saaa_client.subir_archivo(
                file_content=file_content,
                nombre_original=nombre_original or os.path.basename(physical_path),
            )
            self._saaa_upload_cache[cache_key] = {
                "archivo_id": upload.id,
                "path_relativo": upload.path_relativo,
                "app_id": saaa_client.app_id,
                "extension": upload.extension,
            }

            existing = Archivo.objects.filter(
                storage_backend="saaa",
                storage_reference=upload.id,
            ).first()
            if existing:
                return existing, False

            archivo = Archivo(
                storage_backend="saaa",
                storage_reference=upload.id,
                storage_namespace=saaa_client.app_id,
                nombre_original=nombre_original or os.path.basename(physical_path),
                extension=extension or upload.extension,
                mime_type=mime_type or file_meta["mime_type"],
                tamano_bytes=tamano_bytes or file_meta["size"],
                checksum_sha256=sha256 or file_meta["sha256"],
                storage_metadata={**(storage_metadata or {}), "path_relativo": upload.path_relativo},
                subido_por=subido_por,
            )
            archivo.save()
            return archivo, True

        existing = Archivo.objects.filter(
            storage_backend=storage_backend,
            storage_reference=storage_reference,
        ).first()

        if existing:
            return existing, False

        if dry_run:
            return None, True

        archivo = Archivo(
            storage_backend=storage_backend,
            storage_reference=storage_reference,
            storage_namespace=None,
            nombre_original=nombre_original,
            extension=extension,
            mime_type=mime_type,
            tamano_bytes=tamano_bytes,
            checksum_sha256=sha256,
            storage_metadata=storage_metadata,
            subido_por=subido_por,
        )
        archivo.save()
        return archivo, True

    # ── Legacy file analysis ─────────────────────────────────────────────────────

    def _analyze_legacy_files(self, legacy_conn, media_root: Path) -> None:
        """
        Analyze all referenced legacy files and print a report of found/missing.
        Does NOT write any database records.
        """
        self.stdout.write(self.style.WARNING("\n=== LEGACY FILE ANALYSIS ==="))

        reports = []

        # 1. Expediente principal files
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, archivo_principal FROM expedientes_expediente WHERE archivo_principal IS NOT NULL AND archivo_principal != ''")
        rows = cursor.fetchall()
        cursor.close()

        principal_found = principal_missing = 0
        for row in rows:
            path = self._resolve_legacy_file(row["archivo_principal"], media_root)
            status = "FOUND" if path else "MISSING"
            if path:
                principal_found += 1
            else:
                principal_missing += 1
                self.stdout.write(f"  [PRINCIPAL MISSING] expediente={row['id']} path={row['archivo_principal']}")
        reports.append(f"  Expediente principal: {principal_found} found, {principal_missing} missing (total={len(rows)})")

        # 2. Expediente anexo files
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT archivo_anexo FROM expedientes_expedientearchivoanexo WHERE archivo_anexo IS NOT NULL AND archivo_anexo != ''")
        rows = cursor.fetchall()
        cursor.close()

        anexo_found = anexo_missing = 0
        for row in rows:
            path = self._resolve_legacy_file(row["archivo_anexo"], media_root)
            if path:
                anexo_found += 1
            else:
                anexo_missing += 1
                self.stdout.write(f"  [ANEXO MISSING] path={row['archivo_anexo']}")
        reports.append(f"  Expediente anexo: {anexo_found} found, {anexo_missing} missing (total={len(rows)})")

        # 3. Comment files
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT DISTINCT ca.archivo_anexo, ca.comentario_id FROM solicitudes_comentariosolicitudarchivoanexo ca WHERE ca.archivo_anexo IS NOT NULL AND ca.archivo_anexo != ''")
        rows = cursor.fetchall()
        cursor.close()

        comment_found = comment_missing = 0
        for row in rows:
            path = self._resolve_legacy_file(row["archivo_anexo"], media_root)
            if path:
                comment_found += 1
            else:
                comment_missing += 1
                self.stdout.write(f"  [COMENTARIO MISSING] path={row['archivo_anexo']}")
        reports.append(f"  Comentario archivos: {comment_found} found, {comment_missing} missing (total={len(rows)})")

        # 4. Solicitud anexo files
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT DISTINCT sa.archivo_anexo, sa.solicitud_id FROM solicitudes_solicitudarchivoanexo sa WHERE sa.archivo_anexo IS NOT NULL AND sa.archivo_anexo != ''")
        rows = cursor.fetchall()
        cursor.close()

        sol_found = sol_missing = 0
        for row in rows:
            path = self._resolve_legacy_file(row["archivo_anexo"], media_root)
            if path:
                sol_found += 1
            else:
                sol_missing += 1
                self.stdout.write(f"  [SOLICITUD MISSING] path={row['archivo_anexo']}")
        reports.append(f"  Solicitud anexo: {sol_found} found, {sol_missing} missing (total={len(rows)})")

        self.stdout.write(self.style.WARNING("\n--- Summary ---"))
        for r in reports:
            self.stdout.write(self.style.SUCCESS(r))

    # ── Expediente principal file migration ─────────────────────────────────────

    def _migrate_expediente_principal_archivos(
        self, legacy_conn, dry_run: bool, files_backend: str, media_root: Path,
        since: datetime | None = None, expediente_id: uuid.UUID | None = None,
    ) -> int:
        """
        Migrate expedientes_expediente.archivo_principal -> ExpedienteArchivo tipo PRINCIPAL.

        Each expediente can have only one principal file (enforced by UniqueConstraint).
        """
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT e.id AS expediente_uuid,
                   e.archivo_principal,
                   e.fecha_creacion,
                   u.username AS creado_por_username
            FROM expedientes_expediente e
            JOIN auth_user u ON e.creado_por_id = u.id
            WHERE e.archivo_principal IS NOT NULL AND e.archivo_principal != ''
        """
        params = []
        if expediente_id:
            query += " AND e.id = %s"
            params.append(str(expediente_id))
        elif since:
            query += " AND e.fecha_creacion >= %s"
            params.append(since)
        query += " ORDER BY e.fecha_creacion"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()

        count = 0
        for row in rows:
            try:
                expediente = Expediente.objects.get(id=row["expediente_uuid"])
            except Expediente.DoesNotExist:
                continue

            try:
                creado_por = Usuario.objects.get(username=row["creado_por_username"])
            except Usuario.DoesNotExist:
                try:
                    creado_por = Usuario.objects.get(username="admin")
                except Usuario.DoesNotExist:
                    continue

            legacy_path = row["archivo_principal"]
            nombre_original = os.path.basename(legacy_path) or "documento-principal"
            ext = nombre_original.rsplit(".", 1)[-1].lower() if "." in nombre_original else None

            # Resolve physical file
            physical_path = self._resolve_legacy_file(legacy_path, media_root)
            if physical_path is None:
                self.stdout.write(self.style.WARNING(
                    f"    [SKIP] Physical file not found for expediente {expediente.id_publico}: {legacy_path}"
                ))
                continue

            metadata = self._compute_file_metadata(physical_path)

            # storage_reference = legacy path (relative to media_root)
            # For local backend: store the legacy path as-is in storage_reference
            storage_ref = legacy_path.lstrip("/")
            storage_meta = {
                "legacy_path": legacy_path,
                "migrated_from": "expediente_principal",
                "original_checksum": metadata["sha256"],
            }

            if dry_run:
                self.stdout.write(
                    f"    [DRY] ExpedientePrincipal: {expediente.id_publico} -> {nombre_original} "
                    f"({metadata['size']} bytes, backend={files_backend})"
                )
                count += 1
                continue

            # Idempotency: check if Expediente already has a PRINCIPAL archivo
            if ExpedienteArchivo.objects.filter(
                expediente=expediente, tipo_archivo=TipoArchivo.PRINCIPAL
            ).exists():
                continue

            archivo, _ = self._get_or_create_archivo(
                storage_backend=files_backend if files_backend in ("saaa", "saaa-dry") else "local",
                storage_reference=storage_ref,
                nombre_original=nombre_original,
                extension=ext,
                mime_type=metadata["mime_type"],
                tamano_bytes=metadata["size"],
                sha256=metadata["sha256"],
                storage_metadata=storage_meta,
                subido_por=creado_por,
                dry_run=dry_run,
                physical_path=physical_path,
            )
            if archivo is None:
                continue

            ExpedienteArchivo.objects.create(
                expediente=expediente,
                tipo_archivo=TipoArchivo.PRINCIPAL,
                archivo=archivo,
                descripcion="Documento principal migrado desde sistema legacy",
                creado_por=creado_por,
            )
            count += 1

        return count

    # ── Expediente anexo file migration ─────────────────────────────────────────

    def _migrate_expediente_anexo_archivos(
        self, legacy_conn, dry_run: bool, files_backend: str, media_root: Path,
        since: datetime | None = None, expediente_id: uuid.UUID | None = None,
    ) -> int:
        """
        Migrate expedientes_expedientearchivoanexo -> ExpedienteArchivo tipo ANEXO.
        Replaces the old _migrate_archivos with an improved idempotent version.
        """
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT ea.id AS anexo_row_id,
                   ea.archivo_anexo,
                   ea.nombre_original,
                   ea.descripcion,
                   e.id AS expediente_uuid,
                   u.username AS creado_por_username
            FROM expedientes_expedientearchivoanexo ea
            JOIN expedientes_expediente e ON ea.expediente_id = e.id
            JOIN auth_user u ON e.creado_por_id = u.id
        """
        params = []
        if expediente_id:
            query += " WHERE e.id = %s"
            params.append(str(expediente_id))
        elif since:
            # This legacy table has no timestamp used by the current schema.
            # Safely synchronize its rows only as dependencies of new expedientes.
            query += " WHERE e.fecha_creacion >= %s"
            params.append(since)
        query += " ORDER BY e.fecha_creacion"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()

        count = 0
        for row in rows:
            try:
                expediente = Expediente.objects.get(id=row["expediente_uuid"])
            except Expediente.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"    [SKIP] Expediente not found: {row['expediente_uuid']}"
                ))
                continue

            try:
                creado_por = Usuario.objects.get(username=row["creado_por_username"])
            except Usuario.DoesNotExist:
                try:
                    creado_por = Usuario.objects.get(username="admin")
                except Usuario.DoesNotExist:
                    continue

            legacy_path = row["archivo_anexo"]
            nombre_original = row["nombre_original"] or os.path.basename(legacy_path) or "anexo"
            ext = nombre_original.rsplit(".", 1)[-1].lower() if "." in nombre_original else None

            physical_path = self._resolve_legacy_file(legacy_path, media_root)
            if physical_path is None:
                self.stdout.write(self.style.WARNING(
                    f"    [SKIP] Physical file not found: {legacy_path}"
                ))
                continue

            metadata = self._compute_file_metadata(physical_path)
            storage_ref = legacy_path.lstrip("/")
            storage_meta = {
                "legacy_path": legacy_path,
                "migrated_from": "expediente_anexo",
                "legacy_row_id": str(row["anexo_row_id"]),
                "original_checksum": metadata["sha256"],
            }

            if dry_run:
                self.stdout.write(
                    f"    [DRY] ExpedienteAnexo: {expediente.id_publico} -> {nombre_original} "
                    f"({metadata['size']} bytes)"
                )
                count += 1
                continue

            # Idempotency: check if this exact archivo already linked
            expediente_archivo_id = self._legacy_uuid(
                "expediente_archivo_anexo", row["anexo_row_id"]
            )
            if ExpedienteArchivo.objects.filter(id=expediente_archivo_id).exists():
                continue
            existing = ExpedienteArchivo.objects.filter(
                expediente=expediente,
                archivo__storage_backend="local",
                archivo__storage_reference=storage_ref,
            ).select_related("archivo").first()
            if existing:
                continue

            archivo, _ = self._get_or_create_archivo(
                storage_backend=files_backend if files_backend in ("saaa", "saaa-dry") else "local",
                storage_reference=storage_ref,
                nombre_original=nombre_original,
                extension=ext,
                mime_type=metadata["mime_type"],
                tamano_bytes=metadata["size"],
                sha256=metadata["sha256"],
                storage_metadata=storage_meta,
                subido_por=creado_por,
                dry_run=dry_run,
                physical_path=physical_path,
            )
            if archivo is None:
                continue

            ExpedienteArchivo.objects.create(
                id=expediente_archivo_id,
                expediente=expediente,
                tipo_archivo=TipoArchivo.ANEXO,
                archivo=archivo,
                descripcion=row["descripcion"] or "",
                creado_por=creado_por,
            )
            count += 1

        return count

    # ── Comentario -> Mensaje migration ─────────────────────────────────────────

    def _migrate_comentarios_to_mensajes(
        self, legacy_conn, dry_run: bool, files_backend: str, media_root: Path,
        since: datetime | None = None, expediente_id: uuid.UUID | None = None,
    ) -> int:
        """
        Migrate solicitudes_comentariosolicitud -> Mensaje rows.

        For each legacy comment, finds or creates a Conversacion linked to the
        Solicitud (via SolicitudConversacion), then creates a Mensaje in it.

        Idempotency: skips if a Mensaje with the same legacy comentario_id already
        exists (tracked via storage_metadata on the first Archivo in the conversation,
        or by checking if any MensajeArchivoAdjunto references the legacy path).

        Files from solicitudes_comentariosolicitudarchivoanexo are migrated as
        MensajeArchivoAdjunto entries attached to the created Mensaje.
        """
        # First, ensure all solicitudes have a Conversacion
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        solicitud_query = """
            SELECT DISTINCT s.id AS solicitud_uuid,
                   e.id AS expediente_uuid,
                   s.fecha_creacion
            FROM solicitudes_comentariosolicitud c
            JOIN solicitudes_solicitud s ON c.solicitud_id = s.id
            JOIN expedientes_expediente e ON s.expediente_id = e.id
        """
        solicitud_params = []
        if expediente_id:
            solicitud_query += " WHERE e.id = %s"
            solicitud_params.append(str(expediente_id))
        elif since:
            solicitud_query += """ WHERE c.fecha_creacion >= %s OR s.fecha_creacion >= %s
                OR e.fecha_creacion >= %s OR EXISTS (
                    SELECT 1 FROM solicitudes_comentariosolicitudarchivoanexo ca
                    WHERE ca.comentario_id = c.id AND ca.fecha_creacion >= %s
                )"""
            solicitud_params = [since, since, since, since]
        solicitud_query += " ORDER BY s.fecha_creacion"
        cursor.execute(solicitud_query, solicitud_params)
        solicitud_rows = cursor.fetchall()
        cursor.close()

        # Build solicitud -> expediente map
        for srow in solicitud_rows:
            try:
                solicitud = Solicitud.objects.get(id=srow["solicitud_uuid"])
            except Solicitud.DoesNotExist:
                continue

            # Ensure a conversacion exists for this solicitud
            if not hasattr(self, "_solicitud_conversacion_cache"):
                self._solicitud_conversacion_cache = {}

            if solicitud.id not in self._solicitud_conversacion_cache:
                puente = SolicitudConversacion.objects.filter(
                    solicitud=solicitud
                ).select_related("conversacion").first()
                if puente:
                    self._solicitud_conversacion_cache[solicitud.id] = puente.conversacion
                elif not dry_run:
                    conv, _ = Conversacion.objects.get_or_create(
                        titulo=f"Conversación migrated - {solicitud.expediente.id_publico}",
                        defaults={
                            "creada_por": solicitud.creado_por,
                            "fecha_inicio": solicitud.fecha_registro,
                        },
                    )
                    SolicitudConversacion.objects.get_or_create(solicitud=solicitud, conversacion=conv)
                    self._solicitud_conversacion_cache[solicitud.id] = conv

        # Now migrate comments
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        comment_query = """
            SELECT c.id AS legado_id,
                   c.solicitud_id,
                   c.texto,
                   c.fecha_creacion,
                   u.username AS autor_username
            FROM solicitudes_comentariosolicitud c
            JOIN auth_user u ON c.usuario_id = u.id
            JOIN solicitudes_solicitud s ON c.solicitud_id = s.id
            JOIN expedientes_expediente e ON s.expediente_id = e.id
        """
        comment_params = []
        if expediente_id:
            comment_query += " WHERE e.id = %s"
            comment_params.append(str(expediente_id))
        elif since:
            # A new expediente or solicitud carries every dependent comment.
            comment_query += """ WHERE c.fecha_creacion >= %s OR s.fecha_creacion >= %s
                OR e.fecha_creacion >= %s OR EXISTS (
                    SELECT 1 FROM solicitudes_comentariosolicitudarchivoanexo ca
                    WHERE ca.comentario_id = c.id AND ca.fecha_creacion >= %s
                )"""
            comment_params = [since, since, since, since]
        comment_query += " ORDER BY c.fecha_creacion"
        cursor.execute(comment_query, comment_params)
        comment_rows = cursor.fetchall()
        cursor.close()

        count = 0
        if not hasattr(self, "_solicitud_conversacion_cache"):
            self._solicitud_conversacion_cache = {}

        for row in comment_rows:
            try:
                solicitud = Solicitud.objects.get(id=row["solicitud_id"])
            except Solicitud.DoesNotExist:
                continue

            conv = self._solicitud_conversacion_cache.get(solicitud.id)
            if conv is None:
                if dry_run:
                    self.stdout.write(
                        f"    [DRY] Mensaje: legacy_id={row['legado_id']} "
                        f"content={str(row['texto'] or '')[:40]}"
                    )
                    count += 1
                    continue
                # Create conversacion now
                puente = SolicitudConversacion.objects.filter(
                    solicitud=solicitud
                ).select_related("conversacion").first()
                if puente:
                    conv = puente.conversacion
                else:
                    conv, _ = Conversacion.objects.get_or_create(
                        titulo=f"Conversación migrated - {solicitud.expediente.id_publico}",
                        defaults={
                            "creada_por": solicitud.creado_por,
                            "fecha_inicio": solicitud.fecha_registro,
                        },
                    )
                    SolicitudConversacion.objects.get_or_create(solicitud=solicitud, conversacion=conv)
                self._solicitud_conversacion_cache[solicitud.id] = conv

            autor = None
            if row["autor_username"]:
                try:
                    autor = Usuario.objects.get(username=row["autor_username"])
                except Usuario.DoesNotExist:
                    pass

            if dry_run:
                self.stdout.write(
                    f"    [DRY] Mensaje: legacy_id={row['legado_id']} "
                    f"content={str(row['texto'] or '')[:40]}"
                )
                count += 1
                continue

            mensaje_id = self._legacy_uuid("comentario", row["legado_id"])
            mensaje = Mensaje.objects.filter(id=mensaje_id).first()
            if mensaje is None:
                # The initial full migration predates deterministic IDs. Match its
                # immutable legacy payload only to attach a newly added legacy file.
                mensaje = Mensaje.objects.filter(
                    conversacion=conv,
                    autor_usuario=autor,
                    contenido=row["texto"] or "",
                    fecha_envio=row["fecha_creacion"],
                ).first()
            if mensaje is None:
                mensaje = Mensaje.objects.create(
                    id=mensaje_id,
                    conversacion=conv,
                    autor_usuario=autor,
                    contenido=row["texto"] or "",
                    tipo=TipoMensaje.MENSAJE,
                    fecha_envio=row["fecha_creacion"],
                )

            # Migrate attached files for this comment
            self._migrate_legacy_comentario_archivos(
                legacy_conn, mensaje, row["legado_id"], media_root, dry_run, files_backend
            )
            count += 1

        return count

    # ── SolicitudArchivoAnexo migration ─────────────────────────────────────────

    def _migrate_solicitud_archivo_anexos(
        self, legacy_conn, dry_run: bool, files_backend: str, media_root: Path,
        since: datetime | None = None, expediente_id: uuid.UUID | None = None,
    ) -> int:
        """
        Migrate solicitudes_solicitudarchivoanexo -> MensajeArchivoAdjunto.

        Since there is no direct SolicitudArchivo model, these files are attached
        to a migration/system Mensaje in the solicitud's conversation.

        For each solicitud with anexo files, creates a single system Mensaje
        (if not already created for this solicitud) and attaches all files to it.
        """
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT sa.id AS legado_id,
                   sa.solicitud_id,
                   sa.archivo_anexo,
                   sa.descripcion,
                   sa.fecha_creacion,
                   u.username AS subido_por_username
            FROM solicitudes_solicitudarchivoanexo sa
            JOIN solicitudes_solicitud s ON sa.solicitud_id = s.id
            JOIN auth_user u ON s.creado_por_id = u.id
            JOIN expedientes_expediente e ON s.expediente_id = e.id
        """
        params = []
        if expediente_id:
            query += " WHERE e.id = %s"
            params.append(str(expediente_id))
        elif since:
            query += " WHERE sa.fecha_creacion >= %s OR s.fecha_creacion >= %s OR e.fecha_creacion >= %s"
            params = [since, since, since]
        query += " ORDER BY sa.fecha_creacion"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()

        count = 0
        # Cache of migration mensaje per solicitud
        solicitud_mensaje_cache = {}

        for row in rows:
            try:
                solicitud = Solicitud.objects.get(id=row["solicitud_id"])
            except Solicitud.DoesNotExist:
                continue

            legacy_path = row["archivo_anexo"]
            if not legacy_path:
                continue

            nombre_original = os.path.basename(legacy_path) or "anexo"
            ext = nombre_original.rsplit(".", 1)[-1].lower() if "." in nombre_original else None

            physical_path = self._resolve_legacy_file(legacy_path, media_root)
            if physical_path is None:
                self.stdout.write(self.style.WARNING(
                    f"    [SKIP] Solicitud anexo file not found: {legacy_path}"
                ))
                continue

            metadata = self._compute_file_metadata(physical_path)
            storage_ref = legacy_path.lstrip("/")
            storage_meta = {
                "legacy_path": legacy_path,
                "migrated_from": "solicitud_archivo_anexo",
                "legacy_row_id": str(row["legado_id"]),
                "original_checksum": metadata["sha256"],
            }

            subido_por = None
            if row["subido_por_username"]:
                try:
                    subido_por = Usuario.objects.get(username=row["subido_por_username"])
                except Usuario.DoesNotExist:
                    pass

            if dry_run:
                self.stdout.write(
                    f"    [DRY] SolicitudArchivoAnexo: solicitud={solicitud.id} -> {nombre_original} "
                    f"({metadata['size']} bytes)"
                )
                count += 1
                continue

            # Get or create the system migration mensaje for this solicitud
            if solicitud.id not in solicitud_mensaje_cache:
                puente = SolicitudConversacion.objects.filter(
                    solicitud=solicitud
                ).select_related("conversacion").first()
                conv = puente.conversacion if puente else None
                if conv is None:
                    # Create a minimal conversacion
                    conv = Conversacion.objects.create(
                        titulo=f"Sistema - {solicitud.expediente.id_publico}",
                        creada_por=solicitud.creado_por,
                        fecha_inicio=solicitud.fecha_registro,
                    )
                    SolicitudConversacion.objects.create(solicitud=solicitud, conversacion=conv)

                # Check if a migration mensaje already exists for this solicitud
                existing_sys_msg = Mensaje.objects.filter(
                    conversacion=conv,
                    tipo=TipoMensaje.SISTEMA,
                    contenido__startswith="Archivos migrados desde sistema legacy",
                ).first()

                if existing_sys_msg:
                    msg = existing_sys_msg
                else:
                    msg = Mensaje.objects.create(
                        id=self._legacy_uuid("solicitud_archivos_mensaje", solicitud.id),
                        conversacion=conv,
                        autor_usuario=None,
                        contenido="Archivos migrados desde sistema legacy",
                        tipo=TipoMensaje.SISTEMA,
                        fecha_envio=solicitud.fecha_registro,
                    )
                solicitud_mensaje_cache[solicitud.id] = msg
            else:
                msg = solicitud_mensaje_cache[solicitud.id]

            # Idempotency: check if archivo already attached to this mensaje
            adjunto_id = self._legacy_uuid("solicitud_archivo_anexo", row["legado_id"])
            if MensajeArchivoAdjunto.objects.filter(id=adjunto_id).exists():
                continue
            existing_adj = MensajeArchivoAdjunto.objects.filter(
                mensaje=msg,
                archivo__storage_backend="local",
                archivo__storage_reference=storage_ref,
            ).select_related("archivo").first()
            if existing_adj:
                continue

            archivo, _ = self._get_or_create_archivo(
                storage_backend=files_backend if files_backend in ("saaa", "saaa-dry") else "local",
                storage_reference=storage_ref,
                nombre_original=nombre_original,
                extension=ext,
                mime_type=metadata["mime_type"],
                tamano_bytes=metadata["size"],
                sha256=metadata["sha256"],
                storage_metadata=storage_meta,
                subido_por=subido_por,
                dry_run=False,
                physical_path=physical_path,
            )
            if archivo is None:
                continue

            MensajeArchivoAdjunto.objects.create(
                id=adjunto_id,
                mensaje=msg,
                archivo=archivo,
                subido_por=subido_por or msg.conversacion.creada_por,
                fecha_archivo=row["fecha_creacion"],
                descripcion=row["descripcion"] or "",
            )
            count += 1

        return count

    # ── Legacy comentario archivo migration (used by _migrate_comentarios_to_mensajes) ───

    def _migrate_legacy_comentario_archivos(
        self,
        legado_conn,
        mensaje: Mensaje,
        legado_comentario_id: int,
        media_root: Path,
        dry_run: bool,
        files_backend: str = "local",
    ) -> int:
        """
        Migrate archivos for a specific legacy comment (solicitudes_comentariosolicitudarchivoanexo).
        Attaches files as MensajeArchivoAdjunto to the given Mensaje.
        """
        cursor = legado_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT ca.id AS legado_row_id,
                   ca.archivo_anexo,
                   ca.descripcion,
                   ca.fecha_creacion,
                   u.username AS subido_por_username
            FROM solicitudes_comentariosolicitudarchivoanexo ca
            JOIN solicitudes_comentariosolicitud c ON ca.comentario_id = c.id
            JOIN auth_user u ON c.usuario_id = u.id
            WHERE ca.comentario_id = %s
            ORDER BY ca.fecha_creacion
        """, (legado_comentario_id,))
        rows = cursor.fetchall()
        cursor.close()

        count = 0
        for row in rows:
            legacy_path = row["archivo_anexo"]
            if not legacy_path:
                continue

            nombre_original = os.path.basename(legacy_path) or "anexo"
            ext = nombre_original.rsplit(".", 1)[-1].lower() if "." in nombre_original else None

            physical_path = self._resolve_legacy_file(legacy_path, media_root)
            if physical_path is None:
                self.stdout.write(self.style.WARNING(
                    f"    [SKIP] Comment archivo not found: {legacy_path}"
                ))
                continue

            metadata = self._compute_file_metadata(physical_path)
            storage_ref = legacy_path.lstrip("/")
            storage_meta = {
                "legacy_path": legacy_path,
                "migrated_from": "comentario_archivo_anexo",
                "legacy_comentario_id": str(legado_comentario_id),
                "legacy_row_id": str(row["legado_row_id"]),
                "original_checksum": metadata["sha256"],
            }

            subido_por = None
            if row["subido_por_username"]:
                try:
                    subido_por = Usuario.objects.get(username=row["subido_por_username"])
                except Usuario.DoesNotExist:
                    pass

            if dry_run:
                self.stdout.write(
                    f"    [DRY] ComentarioArchivo: mensaje={mensaje.id} -> {nombre_original} "
                    f"({metadata['size']} bytes)"
                )
                count += 1
                continue

            # Idempotency
            adjunto_id = self._legacy_uuid("comentario_archivo_anexo", row["legado_row_id"])
            if MensajeArchivoAdjunto.objects.filter(id=adjunto_id).exists():
                continue
            existing = MensajeArchivoAdjunto.objects.filter(
                mensaje=mensaje,
                archivo__storage_backend="local",
                archivo__storage_reference=storage_ref,
            ).select_related("archivo").first()
            if existing:
                continue

            archivo, _ = self._get_or_create_archivo(
                storage_backend=files_backend if files_backend in ("saaa", "saaa-dry") else "local",
                storage_reference=storage_ref,
                nombre_original=nombre_original,
                extension=ext,
                mime_type=metadata["mime_type"],
                tamano_bytes=metadata["size"],
                sha256=metadata["sha256"],
                storage_metadata=storage_meta,
                subido_por=subido_por,
                dry_run=False,
                physical_path=physical_path,
            )
            if archivo is None:
                continue

            MensajeArchivoAdjunto.objects.create(
                id=adjunto_id,
                mensaje=mensaje,
                archivo=archivo,
                subido_por=subido_por or mensaje.autor_usuario or mensaje.conversacion.creada_por,
                fecha_archivo=row["fecha_creacion"],
                descripcion=row["descripcion"] or "",
            )
            count += 1

        return count

    # ── Conversacion backfill ──────────────────────────────────────────────────────

    def _backfill_conversaciones(
        self, dry_run: bool, since: datetime | None = None,
        expediente_id: uuid.UUID | None = None,
    ) -> int:
        """
        Create an empty Conversacion (and SolicitudConversacion bridge) for
        every Solicitud that does not yet have one.

        Mirrors the behavior of the new SolicitudFlujo._crear_conversacion_vinculada
        which runs as part of the solicitud creation flow. The legacy migration
        copied historical data without triggering that flow, so previously
        migrated solicitudes may have no conversation at all.

        Idempotency: uses get_or_create on SolicitudConversacion, so re-running
        is safe.

        Returns the number of conversaciones actually created.
        """
        admin_user = Usuario.objects.filter(username="admin").first()
        if admin_user is None:
            self.stdout.write(self.style.WARNING(
                "    No admin user found, skipping conversacion backfill."
            ))
            return 0

        qs = Solicitud.objects.exclude(
            id__in=SolicitudConversacion.objects.values_list(
                "solicitud_id", flat=True
            )
        ).select_related("expediente")
        if expediente_id:
            qs = qs.filter(expediente_id=expediente_id)
        elif since:
            qs = qs.filter(fecha_registro__gte=since)

        count = 0
        for solicitud in qs.iterator():
            if dry_run:
                count += 1
                continue

            conv = Conversacion.objects.create(
                titulo=f"Conversación - {solicitud.expediente.id_publico}",
                creada_por=admin_user,
                fecha_inicio=solicitud.fecha_registro,
            )
            SolicitudConversacion.objects.create(
                solicitud=solicitud,
                conversacion=conv,
            )
            count += 1

        return count
