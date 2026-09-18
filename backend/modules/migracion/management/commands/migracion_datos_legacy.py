"""
ETL command to migrate data from legacy mesa_partes database.

Usage:
    python manage.py migracion_datos_legacy
"""

import uuid
from datetime import date, datetime, timedelta

import psycopg2
from psycopg2.extras import RealDictCursor

from django.db import transaction
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.usuarios.domain.models import Area, Usuario, Cargo, AsignacionUsuario
from modules.asignaciones.domain.models import (
    SolicitudAsignacion, SolicitudAsignacionPeriodo, SolicitudAsignacionUsuario,
)
from modules.asignaciones.domain.constants import (
    EstadoPeriodo, TipoCierre, TipoParticipacion, TipoRespuesta,
)
from modules.conversaciones.domain.constants import TipoMensaje
from modules.conversaciones.domain.models import Conversacion, Mensaje, SolicitudConversacion
from modules.tramites.domain.models import (
    Expediente, Solicitud, TipoDocumento,
    ExpedienteArchivo, SolicitudArchivo, SolicitudEstadoHistorial, SolicitudRespuesta,
)
from modules.tramites.domain.constants import EstadoSolicitud, Prioridad, TipoPersona, TipoArchivo
from modules.tramites.domain.models.solicitud_historial import OrigenCambio


# Legacy database connection
LEGACY_DB = {
    'host': 'localhost',
    'port': 15433,
    'dbname': 'mesa_partes_db',
    'user': 'postgres',
    'password': 'postgres',
}

# Legacy media path (where files are stored)
LEGACY_MEDIA_PATH = '/var/lib/postgresql/mesa_partes_media'


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

    def handle(self, *args, **options) -> None:
        dry_run: bool = options["dry_run"]
        skip_files: bool = options["skip_files"]

        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write(self.style.WARNING("MIGRATION: migracion_datos_legacy"))
        self.stdout.write(self.style.WARNING("=" * 60))

        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY RUN MODE]"))

        # Connect to legacy database
        try:
            legacy_conn = psycopg2.connect(**LEGACY_DB)
            legacy_conn.autocommit = True
            self.stdout.write(self.style.SUCCESS(f"Connected to legacy DB: {LEGACY_DB['dbname']}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to connect to legacy DB: {e}"))
            return

        # Run migration in atomic transaction
        with transaction.atomic():
            if dry_run:
                self.stdout.write(self.style.WARNING("[DRY RUN] Would migrate:"))

            # 1. Migrate users
            users_count = self._migrate_users(legacy_conn, dry_run)
            self.stdout.write(self.style.SUCCESS(f"  Users migrated: {users_count}"))

            # 2. Migrate areas (from seeds, already loaded)
            areas_count = Area.objects.count()
            self.stdout.write(self.style.SUCCESS(f"  Areas (from seeds): {areas_count}"))

            # 3. Migrate TipoDocumento (from seeds, already loaded)
            td_count = TipoDocumento.objects.count()
            self.stdout.write(self.style.SUCCESS(f"  TipoDocumento (from seeds): {td_count}"))

            # 4. Migrate asignaciones (AsignacionUsuario for adjuntados)
            asignaciones_count = self._migrate_asignaciones(legacy_conn, dry_run)
            self.stdout.write(self.style.SUCCESS(f"  Asignaciones migrated: {asignaciones_count}"))

            # 5. Migrate expedientes
            exp_count = self._migrate_expedientes(legacy_conn, dry_run)
            self.stdout.write(self.style.SUCCESS(f"  Expedientes migrated: {exp_count}"))

            # 6. Migrar solicitudes
            sol_count = self._migrate_solicitudes(legacy_conn, dry_run)
            self.stdout.write(self.style.SUCCESS(f"  Solicitudes migrated: {sol_count}"))

            # 7. Migrar historial de estados y respuestas finales
            historial_count = self._migrate_historial_estados(legacy_conn, dry_run)
            self.stdout.write(self.style.SUCCESS(f"  Historial estados migrated: {historial_count}"))

            respuestas_count = self._migrate_respuestas_finales(legacy_conn, dry_run)
            self.stdout.write(self.style.SUCCESS(f"  Respuestas finales migrated: {respuestas_count}"))

            # 8. Migrate files (ExpedienteArchivo and SolicitudArchivo)
            if not skip_files:
                archivos_count = self._migrate_archivos(legacy_conn, dry_run)
                self.stdout.write(self.style.SUCCESS(f"  Archivos migrated: {archivos_count}"))
            else:
                self.stdout.write(self.style.WARNING("  Skipping files (--skip-files)"))

        legacy_conn.close()

        self.stdout.write(self.style.SUCCESS("\nMigration completed successfully!"))

    def _migrate_users(self, legacy_conn, dry_run: bool) -> int:
        """Migrate 102 users from legacy auth_user table."""
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, username, email, first_name, last_name, is_staff, is_active
            FROM auth_user
            ORDER BY id
        """)
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

    def _migrate_asignaciones(self, legacy_conn, dry_run: bool) -> int:
        """
        Migrate AsignacionUsuario from the union of:
         - usuario_asignado_id in solicitudes_solicitud (area principal)
         - usuario_id in solicitudes_usuariosolicitudadjuntado (adjuntados)
        Each user's area comes from their perfil (usuarios_perfilusuario.area_id).
        """
        # Union of assigned users (area principal) + adjuntados, with their profile area
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT DISTINCT u.id AS user_id, u.username, a.nombre AS area_nombre
            FROM (
                SELECT DISTINCT s.usuario_asignado_id AS uid
                FROM solicitudes_solicitud s
                UNION
                SELECT DISTINCT ua.usuario_id
                FROM solicitudes_usuariosolicitudadjuntado ua
            ) x
            JOIN auth_user u ON u.id = x.uid
            JOIN usuarios_perfilusuario up ON up.user_id = u.id
            JOIN usuarios_area a ON up.area_id = a.id
            WHERE up.area_id IS NOT NULL
            ORDER BY u.username
        """)
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

    def _migrate_expedientes(self, legacy_conn, dry_run: bool) -> int:
        """Migrate 487 expedientes, preserving legacy UUIDs."""
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT e.*, u.username as creado_por_username
            FROM expedientes_expediente e
            JOIN auth_user u ON e.creado_por_id = u.id
            ORDER BY e.fecha_creacion
        """)
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
            try:
                tipo_documento = TipoDocumento.objects.get(nombre=tipo_doc_nombre)
            except TipoDocumento.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"    TipoDocumento not found: {tipo_doc_nombre}"))
                continue

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

    def _migrate_solicitudes(self, legacy_conn, dry_run: bool) -> int:
        """Migrate 480 solicitudes, mapping states and preserving UUIDs."""
        # Map legacy states -> new states
        STATE_MAP = {
            'CERRADO': EstadoSolicitud.FINALIZADA,
            'ENVIADO_A_AREA': EstadoSolicitud.EN_TRAMITE,
            'EN_GESTION_MP': EstadoSolicitud.EN_GESTION,
            'REENVIO_MP': EstadoSolicitud.EN_TRAMITE,
        }

        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
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
            ORDER BY s.fecha_creacion
        """)
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

    def _migrate_historial_estados(self, legacy_conn, dry_run: bool) -> int:
        """Migrate legacy django-simple-history rows into SolicitudEstadoHistorial."""
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT h.id AS solicitud_id,
                   h.estado,
                   h.finalizado,
                   h.history_id,
                   h.history_date,
                   h.history_type,
                   h.history_user_id,
                   h.creado_por_id,
                   s.creado_por_id AS solicitud_creado_por_id
            FROM solicitudes_historicalsolicitud h
            JOIN solicitudes_solicitud s ON s.id = h.id
            ORDER BY h.id, h.history_date, h.history_id
        """)
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

            if SolicitudEstadoHistorial.objects.filter(solicitud=solicitud).exists():
                continue

            first = history_rows[0]
            creado_por = self._legacy_user(
                legacy_conn,
                first.get("solicitud_creado_por_id") or first.get("creado_por_id"),
            ) or solicitud.creado_por

            artificial_fecha = first["history_date"] - timedelta(hours=2)
            if dry_run:
                count += 1
            else:
                SolicitudEstadoHistorial.objects.create(
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
                        solicitud=solicitud,
                        estado_anterior=previous_estado,
                        estado_nuevo=mapped_estado,
                        fecha_cambio=row["history_date"],
                        cambiado_por=cambiado_por,
                        motivo="Migrado desde historial legacy",
                        observacion=None,
                        origen=origen,
                    )
                    count += 1
                previous_estado = mapped_estado

        return count

    def _migrate_respuestas_finales(self, legacy_conn, dry_run: bool) -> int:
        """Create final CONFORMIDAD responses for truly finalized legacy solicitudes."""
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT s.id,
                   s.fecha_cierre,
                   s.modificado_por_id,
                   s.usuario_asignado_id
            FROM solicitudes_solicitud s
            WHERE s.estado = 'CERRADO' AND s.finalizado = true
            ORDER BY s.fecha_cierre
        """)
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

    def _migrate_archivos(self, legacy_conn, dry_run: bool) -> int:
        """Migrate 4 ExpedienteArchivos and 6 SolicitudArchivos."""
        count = 0

        # Migrate ExpedienteArchivos
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT ea.*, e.id as expediente_uuid, u.username as creado_por_username
            FROM expedientes_expedientearchivoanexo ea
            JOIN expedientes_expediente e ON ea.expediente_id = e.id
            JOIN auth_user u ON e.creado_por_id = u.id
        """)
        exp_archivos = cursor.fetchall()
        cursor.close()

        for row in exp_archivos:
            try:
                expediente = Expediente.objects.get(id=row['expediente_uuid'])
            except Expediente.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"    Expediente not found for archivo: {row['expediente_uuid']}"))
                continue

            try:
                creado_por = Usuario.objects.get(username=row['creado_por_username'])
            except Usuario.DoesNotExist:
                try:
                    creado_por = Usuario.objects.get(username='admin')
                except Usuario.DoesNotExist:
                    continue

            if dry_run:
                self.stdout.write(f"    [DRY] ExpedienteArchivo: {row['archivo_anexo']}")
                count += 1
                continue

            # Get or create the file record
            archivo_name = row['archivo_anexo']
            nombre_original = row['nombre_original'] or 'anexo'
            descripcion = row['descripcion'] or ''

            # For the FileField, we store the path but don't actually copy the file
            # The file path will be used to verify physical file existence
            archivo_path = archivo_name  # This would be the relative path

            archivo, created = ExpedienteArchivo.objects.get_or_create(
                expediente=expediente,
                defaults={
                    'tipo_archivo': TipoArchivo.ANEXO,  # All migrated files are ANEXO
                    'archivo': archivo_path,  # Path reference
                    'nombre_original': nombre_original,
                    'descripcion': descripcion,
                    'creado_por': creado_por,
                }
            )
            if created:
                count += 1

        # Migrate SolicitudArchivos
        cursor = legacy_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT sa.*, s.id as solicitud_uuid, u.username as creado_por_username
            FROM solicitudes_solicitudarchivoanexo sa
            JOIN solicitudes_solicitud s ON sa.solicitud_id = s.id
            JOIN auth_user u ON s.creado_por_id = u.id
        """)
        sol_archivos = cursor.fetchall()
        cursor.close()

        for row in sol_archivos:
            try:
                solicitud = Solicitud.objects.get(id=row['solicitud_uuid'])
            except Solicitud.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"    Solicitud not found for archivo: {row['solicitud_uuid']}"))
                continue

            try:
                creado_por = Usuario.objects.get(username=row['creado_por_username'])
            except Usuario.DoesNotExist:
                try:
                    creado_por = Usuario.objects.get(username='admin')
                except Usuario.DoesNotExist:
                    continue

            if dry_run:
                self.stdout.write(f"    [DRY] SolicitudArchivo: {row['archivo_anexo']}")
                count += 1
                continue

            archivo_name = row['archivo_anexo']
            descripcion = row['descripcion'] or ''

            archivo, created = SolicitudArchivo.objects.get_or_create(
                solicitud=solicitud,
                defaults={
                    'archivo': archivo_name,
                    'nombre_original': archivo_name.split('/')[-1] if '/' in archivo_name else archivo_name,
                    'descripcion': descripcion,
                    'creado_por': creado_por,
                }
            )
            if created:
                count += 1

        return count
