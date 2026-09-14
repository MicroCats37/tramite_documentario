"""
Unit tests for NotificacionService.

Tests the sync service methods for notification generation.
pytest-django provides transaction isolation per test — no explicit rollback needed.
"""

from datetime import datetime, date

import pytest
from django.contrib.auth import get_user_model

# Constants from canonical location
from modules.notificaciones.domain.constants import (
    AmbitoNotificacion,
    EventoNotificacion,
    PrioridadNotificacion,
)
# Notification models moved to modules.notificaciones
from modules.notificaciones.domain.models import (
    Notificacion,
    NotificacionArea,
    NotificacionAsignacion,
    NotificacionPeriodo,
    NotificacionSolicitud,
    NotificacionUsuario,
)
# Service re-exported from new location
from modules.notificaciones.domain.services.core.notificacion_service import NotificacionService
from modules.tramites.domain.models import Expediente, Solicitud
from modules.tramites.domain.constants import EstadoSolicitud, Prioridad
from modules.usuarios.domain.models import Area


@pytest.fixture
def cargo_test(db):
    """Create a test cargo (position/role)."""
    from modules.usuarios.domain.models.cargo import Cargo
    return Cargo.objects.create(
        nombre="Cargo de Prueba",
        activo=True,
    )


@pytest.fixture
def area_test(db):
    """Create a test area."""
    return Area.objects.create(
        nombre="Área de Prueba",
        descripcion="Área para tests de notificación",
        activo=True,
    )


@pytest.fixture
def usuario_test(db):
    """Create a test user."""
    User = get_user_model()
    return User.objects.create_user(
        username="test_notif",
        email="test_notif@cip.gob.pe",
        password="testpass123",
        dni="12345678",
        nombres="Test",
        apellidos="Notif",
    )


@pytest.fixture
def usuario_test_2(db):
    """Create a second test user in the same area."""
    User = get_user_model()
    return User.objects.create_user(
        username="test_notif_2",
        email="test_notif_2@cip.gob.pe",
        password="testpass123",
        dni="22345678",
        nombres="Test2",
        apellidos="Notif2",
    )


@pytest.fixture
def usuario_inactivo(db):
    """Create an inactive user for eligibility tests."""
    User = get_user_model()
    return User.objects.create_user(
        username="test_inactivo",
        email="test_inactivo@cip.gob.pe",
        password="testpass123",
        dni="32345678",
        nombres="Test",
        apellidos="Inactivo",
        is_active=False,
    )


@pytest.fixture
def usuario_sin_asignacion(db):
    """Create a user without area assignment."""
    User = get_user_model()
    return User.objects.create_user(
        username="test_sin_asign",
        email="test_sin_asign@cip.gob.pe",
        password="testpass123",
        dni="42345678",
        nombres="Test",
        apellidos="SinAsign",
    )


@pytest.fixture
def asignacion_usuario_activa(db, usuario_test, area_test, cargo_test):
    """Create an active user-area assignment."""
    from modules.usuarios.domain.models.asignacion_usuario import AsignacionUsuario
    return AsignacionUsuario.objects.create(
        usuario=usuario_test,
        area=area_test,
        cargo=cargo_test,
        periodo_inicio=date.today(),
        periodo_fin=None,  # Activa
    )


@pytest.fixture
def asignacion_usuario_activa_2(db, usuario_test_2, area_test, cargo_test):
    """Create a second active user-area assignment."""
    from modules.usuarios.domain.models.asignacion_usuario import AsignacionUsuario
    return AsignacionUsuario.objects.create(
        usuario=usuario_test_2,
        area=area_test,
        cargo=cargo_test,
        periodo_inicio=date.today(),
        periodo_fin=None,
    )


@pytest.fixture
def expediente_test(db, usuario_test):
    """Create a test expediente."""
    from modules.tramites.domain.models import TipoDocumento
    td = TipoDocumento.objects.get_or_create(
        nombre="SOLICITUD",
        descripcion="Solicitud",
    )[0]
    return Expediente.objects.create(
        numero=9999,
        tipo_persona="NATURAL",
        dni="12345678",
        nombres="Juan",
        apellidos="Perez",
        correo="juan@test.com",
        telefono="999888777",
        tipo_documento=td,
        numero_documento="DOC-TEST-001",
        numero_folios=5,
        asunto="Trámite de prueba para notificación",
        fecha_registro=datetime.now(),
        creado_por=usuario_test,
    )


@pytest.fixture
def solicitud_test(db, expediente_test, usuario_test):
    """Create a test solicitud."""
    return Solicitud.objects.create(
        expediente=expediente_test,
        estado=EstadoSolicitud.EN_GESTION,
        prioridad=Prioridad.MEDIA,
        fecha_registro=datetime.now(),
        creado_por=usuario_test,
    )


@pytest.fixture
def service():
    """Return a NotificacionService instance."""
    return NotificacionService()


# ── Tests for crear_notificacion_area ─────────────────────────────────────────


@pytest.mark.django_db
def test_crear_notificacion_area_minima(
    service, area_test, usuario_test, asignacion_usuario_activa
):
    """
    GIVEN:  a valid area with an active user assignment
    WHEN:  crear_notificacion_area is called with only required fields
    THEN:  a Notificacion is created with audiencia_tipo=AREA
           and one NotificacionUsuario is created for the eligible user
    """
    notificacion = service.crear_notificacion_area(
        area=area_test,
        titulo="Notificación mínima",
        mensaje="Mensaje de prueba",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
    )

    assert notificacion is not None
    # area removed from Notificacion FK — area is now via NotificacionArea
    assert notificacion.areas_notificadas.first().area == area_test
    assert notificacion.ambito == AmbitoNotificacion.SOLICITUD
    assert notificacion.evento == EventoNotificacion.ASIGNACION_CREADA
    assert notificacion.prioridad == PrioridadNotificacion.NORMAL
    assert notificacion.titulo == "Notificación mínima"
    assert notificacion.mensaje == "Mensaje de prueba"
    assert notificacion.generada_por_id == usuario_test.id

    # NotificacionUsuario para el usuario elegible
    nus = list(notificacion.usuarios_notificados.all())
    assert len(nus) == 1
    assert nus[0].usuario == usuario_test

    # NotificacionArea creada
    assert notificacion.areas_notificadas.count() == 1
    assert notificacion.areas_notificadas.first().area == area_test


@pytest.mark.django_db
def test_crear_notificacion_area_con_solicitud(
    service, area_test, usuario_test, asignacion_usuario_activa, solicitud_test
):
    """
    GIVEN:  a valid area with an active user assignment and a solicitud
    WHEN:  crear_notificacion_area is called with solicitud
    THEN:  NotificacionSolicitud context is created
    """
    notificacion = service.crear_notificacion_area(
        area=area_test,
        titulo="Notificación con solicitud",
        mensaje="Mensaje con solicitud",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
        solicitud=solicitud_test,
    )

    # solicitud is now via NotificacionSolicitud link table
    assert notificacion.contexto_solicitud.first().solicitud == solicitud_test

    # NotificacionSolicitud creada
    contexto_solicitud = notificacion.contexto_solicitud.first()
    assert contexto_solicitud is not None
    assert contexto_solicitud.solicitud == solicitud_test


@pytest.mark.django_db
def test_crear_notificacion_area_solo_area_sin_usuarios(
    service, area_test, usuario_sin_asignacion
):
    """
    GIVEN:  an area with no active user assignments
    WHEN:  crear_notificacion_area is called
    THEN:  the Notificacion is created but no NotificacionUsuario records exist
    """
    notificacion = service.crear_notificacion_area(
        area=area_test,
        titulo="Notificación sin usuarios",
        mensaje="Ningún usuario elegible",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.RECORDATORIO,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_sin_asignacion.id,
        ocurrido_en=datetime.now(),
    )

    assert notificacion is not None
    assert notificacion.usuarios_notificados.count() == 0


@pytest.mark.django_db
def test_crear_notificacion_area_multiple_usuarios(
    service, area_test, usuario_test, usuario_test_2,
    asignacion_usuario_activa, asignacion_usuario_activa_2
):
    """
    GIVEN:  an area with two active user assignments
    WHEN:  crear_notificacion_area is called
    THEN:  two NotificacionUsuario records are created
    """
    notificacion = service.crear_notificacion_area(
        area=area_test,
        titulo="Notificación múltiples usuarios",
        mensaje="Dos usuarios elegibles",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
    )

    nus = list(notificacion.usuarios_notificados.all())
    assert len(nus) == 2
    usuarios_ids = {nu.usuario_id for nu in nus}
    assert usuarios_ids == {usuario_test.id, usuario_test_2.id}


@pytest.mark.django_db
def test_crear_notificacion_area_excluye_usuario_inactivo(
    service, area_test, usuario_test, usuario_inactivo, asignacion_usuario_activa, cargo_test
):
    """
    GIVEN:  an area with one active and one inactive user assignment
    WHEN:  crear_notificacion_area is called
    THEN:  only the active user's NotificacionUsuario is created
    """
    # Create inactive user assignment
    from modules.usuarios.domain.models.asignacion_usuario import AsignacionUsuario
    AsignacionUsuario.objects.create(
        usuario=usuario_inactivo,
        area=area_test,
        cargo=cargo_test,
        periodo_inicio=date.today(),
        periodo_fin=None,
    )

    notificacion = service.crear_notificacion_area(
        area=area_test,
        titulo="Notificación excluye inactivos",
        mensaje="Solo activos",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
    )

    nus = list(notificacion.usuarios_notificados.all())
    assert len(nus) == 1
    assert nus[0].usuario == usuario_test


@pytest.mark.django_db
def test_crear_notificacion_area_notificacion_area_unico(
    service, area_test, usuario_test, asignacion_usuario_activa
):
    """
    GIVEN:  two notifications created for the same area
    WHEN:  each notification gets its own NotificacionArea via get_or_create
    THEN:  no duplicate NotificacionArea per notification, but each notification has one
    """
    # First notification
    notif1 = service.crear_notificacion_area(
        area=area_test,
        titulo="Primera notificación",
        mensaje="Primera",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
    )

    # Second notification
    notif2 = service.crear_notificacion_area(
        area=area_test,
        titulo="Segunda notificación",
        mensaje="Segunda",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
    )

    assert notif1.id != notif2.id

    # Each has its own NotificacionArea
    assert notif1.areas_notificadas.count() == 1
    assert notif2.areas_notificadas.count() == 1
    assert notif1.areas_notificadas.first().area == area_test
    assert notif2.areas_notificadas.first().area == area_test

    # NotificacionArea records are distinct
    na1 = notif1.areas_notificadas.first()
    na2 = notif2.areas_notificadas.first()
    assert na1.id != na2.id


@pytest.mark.django_db
def test_crear_notificacion_area_idempotencia_usuario(
    service, area_test, usuario_test, asignacion_usuario_activa
):
    """
    GIVEN:  two different notifications created for the same user
    WHEN:  each notification has its own NotificacionUsuario via get_or_create
    THEN:  each notification has one NotificacionUsuario, distinct records
    """
    # Create first notification
    notif1 = service.crear_notificacion_area(
        area=area_test,
        titulo="Primera",
        mensaje="Primera",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
    )

    # Second notification (different notification but same user)
    notif2 = service.crear_notificacion_area(
        area=area_test,
        titulo="Segunda",
        mensaje="Segunda",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.RECORDATORIO,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
    )

    # Each notification has its own NotificacionUsuario
    assert notif1.usuarios_notificados.count() == 1
    assert notif2.usuarios_notificados.count() == 1
    assert notif1.usuarios_notificados.first().usuario == usuario_test
    assert notif2.usuarios_notificados.first().usuario == usuario_test

    # They are distinct records
    nu1 = notif1.usuarios_notificados.first()
    nu2 = notif2.usuarios_notificados.first()
    assert nu1.id != nu2.id


@pytest.mark.django_db
def test_crear_notificacion_area_con_mensaje_null(
    service, area_test, usuario_test, asignacion_usuario_activa
):
    """
    GIVEN:  crear_notificacion_area is called with mensaje=None
    THEN:  the Notificacion is created with null mensaje
    """
    notificacion = service.crear_notificacion_area(
        area=area_test,
        titulo="Sin mensaje",
        mensaje=None,
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.ALTA,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
    )

    assert notificacion.mensaje is None
    assert notificacion.titulo == "Sin mensaje"


@pytest.mark.django_db
def test_crear_notificacion_usuario_creates_notificacion_and_usuario(service, usuario_test):
    """
    GIVEN:  a valid usuario
    WHEN:  crear_notificacion_usuario is called
    THEN:  a Notificacion is created with audiencia_tipo=USUARIO
            and one NotificacionUsuario is created for the target user
            and no NotificacionArea is created
    """
    notificacion = service.crear_notificacion_usuario(
        usuario_id=usuario_test.id,
        titulo="Notificación directa a usuario",
        mensaje="Mensaje de prueba",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.COMENTARIO_MENCION,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
    )

    assert notificacion is not None
    assert notificacion.ambito == AmbitoNotificacion.SOLICITUD
    assert notificacion.evento == EventoNotificacion.COMENTARIO_MENCION
    assert notificacion.titulo == "Notificación directa a usuario"

    # NotificacionUsuario created for target user
    nus = list(notificacion.usuarios_notificados.all())
    assert len(nus) == 1
    assert nus[0].usuario == usuario_test

    # No NotificacionArea (user-targeted, not area-targeted)
    assert notificacion.areas_notificadas.count() == 0


@pytest.mark.django_db
def test_crear_notificacion_usuario_all_mentioned_users_get_notification(
    service, db
):
    """
    GIVEN:  multiple mentioned users
    WHEN:  _notify_menciones iterates over all menciones
    THEN:  each user gets their own NotificacionUsuario row
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user1 = User.objects.create_user(
        username="mencion_1", email="m1@test.com", password="pass",
        dni="11111111", nombres="M", apellidos="One"
    )
    user2 = User.objects.create_user(
        username="mencion_2", email="m2@test.com", password="pass",
        dni="22222222", nombres="M", apellidos="Two"
    )

    # Create two separate notifications via crear_notificacion_usuario
    notif1 = service.crear_notificacion_usuario(
        usuario_id=user1.id,
        titulo="Mencion a user1",
        mensaje="Contenido",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.COMENTARIO_MENCION,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=user1.id,
        ocurrido_en=datetime.now(),
    )
    notif2 = service.crear_notificacion_usuario(
        usuario_id=user2.id,
        titulo="Mencion a user2",
        mensaje="Contenido",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.COMENTARIO_MENCION,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=user2.id,
        ocurrido_en=datetime.now(),
    )

    # Each notification has exactly one NotificacionUsuario
    assert notif1.usuarios_notificados.count() == 1
    assert notif1.usuarios_notificados.first().usuario == user1
    assert notif2.usuarios_notificados.count() == 1
    assert notif2.usuarios_notificados.first().usuario == user2

    # No cross-contamination
    assert notif1.usuarios_notificados.filter(usuario=user2).count() == 0
    assert notif2.usuarios_notificados.filter(usuario=user1).count() == 0


# ── Tests for crear_notificacion_usuario with expanded context ─────────────────


@pytest.mark.django_db
def test_crear_notificacion_usuario_solicitud_only(
    service, usuario_test, solicitud_test
):
    """
    GIVEN:  a valid usuario and solicitud
    WHEN:  crear_notificacion_usuario is called with only solicitud
    THEN:  NotificacionSolicitud is created with solicitud
            and conversacion/mensaje/asignacion/periodo are null
    """
    from modules.notificaciones.domain.models import NotificacionSolicitud

    notificacion = service.crear_notificacion_usuario(
        usuario_id=usuario_test.id,
        titulo="Notificación solo solicitud",
        mensaje="Sin contexto adicional",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.COMENTARIO_MENCION,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
        solicitud=solicitud_test,
    )

    assert notificacion is not None

    # NotificacionSolicitud created with solicitud
    contexto = NotificacionSolicitud.objects.get(notificacion=notificacion)
    assert contexto.solicitud == solicitud_test
    assert contexto.conversacion is None
    assert contexto.mensaje is None
    assert contexto.asignacion is None
    assert contexto.periodo is None


@pytest.mark.django_db
def test_crear_notificacion_usuario_with_asignacion_and_periodo(
    service, usuario_test, solicitud_test, area_test
):
    """
    GIVEN:  a valid usuario, solicitud, and asignacion
    WHEN:  crear_notificacion_usuario is called with asignacion and periodo
    THEN:  NotificacionSolicitud is created with all context fields populated
    """
    from datetime import date
    from modules.asignaciones.domain.models import SolicitudAsignacion
    from modules.notificaciones.domain.models import NotificacionSolicitud

    # Create asignacion
    asignacion = SolicitudAsignacion.objects.create(
        solicitud=solicitud_test,
        area=area_test,
        fecha_incorporacion=datetime.now(),
        incorporado_por=usuario_test,
    )

    # Create periodo (SolicitudAsignacionPeriodo)
    from modules.asignaciones.domain.models import SolicitudAsignacionPeriodo
    periodo = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        fecha_inicio=date.today(),
    )

    notificacion = service.crear_notificacion_usuario(
        usuario_id=usuario_test.id,
        titulo="Notificación con asignacion y periodo",
        mensaje="Contexto completo",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
        solicitud=solicitud_test,
        asignacion=asignacion,
        periodo=periodo,
    )

    assert notificacion is not None

    # Verify NotificacionSolicitud has all context
    contexto = NotificacionSolicitud.objects.get(notificacion=notificacion)
    assert contexto.solicitud == solicitud_test
    assert contexto.asignacion == asignacion
    assert contexto.periodo == periodo
    assert contexto.conversacion is None
    assert contexto.mensaje is None


@pytest.mark.django_db
def test_crear_notificacion_usuario_with_conversacion_and_mensaje(
    service, usuario_test, solicitud_test
):
    """
    GIVEN:  a valid usuario, solicitud, conversacion and mensaje
    WHEN:  crear_notificacion_usuario is called with conversacion_id and mensaje_id
    THEN:  NotificacionSolicitud is created with conversacion and mensaje context
            (this is the mention notification pattern)
    """
    from datetime import date
    from modules.conversaciones.domain.models import Conversacion, Mensaje
    from modules.conversaciones.domain.constants import TipoMensaje
    from modules.notificaciones.domain.models import NotificacionSolicitud

    # Create conversacion
    conversacion = Conversacion.objects.create(
        titulo="Conversación de prueba",
        creada_por=usuario_test,
        fecha_inicio=datetime.now(),
    )

    # Create mensaje
    mensaje = Mensaje.objects.create(
        conversacion=conversacion,
        autor_usuario=usuario_test,
        contenido="Mensaje con mención",
        tipo=TipoMensaje.MENSAJE,
        fecha_envio=datetime.now(),
    )

    notificacion = service.crear_notificacion_usuario(
        usuario_id=usuario_test.id,
        titulo="Mencionaste a alguien",
        mensaje="Te mencionaron en un comentario",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.COMENTARIO_MENCION,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
        solicitud=solicitud_test,
        conversacion_id=conversacion.id,
        mensaje_id=mensaje.id,
    )

    assert notificacion is not None

    # Verify NotificacionSolicitud has conversacion and mensaje
    contexto = NotificacionSolicitud.objects.get(notificacion=notificacion)
    assert contexto.solicitud == solicitud_test
    assert contexto.conversacion == conversacion
    assert contexto.mensaje == mensaje
    # Other fields null
    assert contexto.asignacion is None
    assert contexto.periodo is None


@pytest.mark.django_db
def test_crear_notificacion_usuario_with_all_context(
    service, usuario_test, solicitud_test, area_test
):
    """
    GIVEN:  all context fields available
    WHEN:  crear_notificacion_usuario is called with conversacion, mensaje,
           asignacion, and periodo
    THEN:  NotificacionSolicitud is created with all fields populated
    """
    from datetime import date
    from modules.asignaciones.domain.models import SolicitudAsignacion, SolicitudAsignacionPeriodo
    from modules.conversaciones.domain.models import Conversacion, Mensaje
    from modules.conversaciones.domain.constants import TipoMensaje
    from modules.notificaciones.domain.models import NotificacionSolicitud

    # Create conversacion and mensaje
    conversacion = Conversacion.objects.create(
        titulo="Conversación full",
        creada_por=usuario_test,
        fecha_inicio=datetime.now(),
    )
    mensaje = Mensaje.objects.create(
        conversacion=conversacion,
        autor_usuario=usuario_test,
        contenido="Mensaje full",
        tipo=TipoMensaje.MENSAJE,
        fecha_envio=datetime.now(),
    )

    # Create asignacion and periodo
    asignacion = SolicitudAsignacion.objects.create(
        solicitud=solicitud_test,
        area=area_test,
        fecha_incorporacion=datetime.now(),
        incorporado_por=usuario_test,
    )
    periodo = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        fecha_inicio=date.today(),
    )

    notificacion = service.crear_notificacion_usuario(
        usuario_id=usuario_test.id,
        titulo="Notificación contexto completo",
        mensaje="Todos los campos",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.COMENTARIO_MENCION,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
        solicitud=solicitud_test,
        asignacion=asignacion,
        periodo=periodo,
        conversacion_id=conversacion.id,
        mensaje_id=mensaje.id,
    )

    assert notificacion is not None

    # Verify all fields
    contexto = NotificacionSolicitud.objects.get(notificacion=notificacion)
    assert contexto.solicitud == solicitud_test
    assert contexto.asignacion == asignacion
    assert contexto.periodo == periodo
    assert contexto.conversacion == conversacion
    assert contexto.mensaje == mensaje


# ── Tests for crear_notificacion_area with expanded NotificacionSolicitud ─────


@pytest.mark.django_db
def test_crear_notificacion_area_con_asignacion_en_solicitud_context(
    service, area_test, usuario_test, asignacion_usuario_activa, solicitud_test
):
    """
    GIVEN:  a valid area with active user, a solicitud, and an asignacion
    WHEN:  crear_notificacion_area is called with solicitud and asignacion
    THEN:  NotificacionSolicitud is created with asignacion in its fields
            (not in legacy NotificacionAsignacion table)
    """
    from datetime import date
    from modules.asignaciones.domain.models import SolicitudAsignacion, SolicitudAsignacionPeriodo
    from modules.notificaciones.domain.models import NotificacionSolicitud

    # Create asignacion
    asignacion = SolicitudAsignacion.objects.create(
        solicitud=solicitud_test,
        area=area_test,
        fecha_incorporacion=datetime.now(),
        incorporado_por=usuario_test,
    )

    # Create periodo
    periodo = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        fecha_inicio=date.today(),
    )

    notificacion = service.crear_notificacion_area(
        area=area_test,
        titulo="Notificación area con asignacion",
        mensaje="Con asignacion en contexto",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
        solicitud=solicitud_test,
        asignacion=asignacion,
        periodo=periodo,
    )

    assert notificacion is not None

    # Verify NotificacionSolicitud has asignacion and periodo
    contexto = NotificacionSolicitud.objects.get(notificacion=notificacion)
    assert contexto.solicitud == solicitud_test
    assert contexto.asignacion == asignacion
    assert contexto.periodo == periodo
