"""
E2E tests for Notificacion GET API.

Tests the /notificaciones and /notificaciones/{id} endpoints.

Uses ninja_extra.testing.TestClient (sync) per TEST_ARCHITECTURE_CONTRACT.
Controllers are now sync (contrato P3).

URLs: GET /notificaciones
      GET /notificaciones/{id}
"""
from datetime import datetime

import pytest
from django.contrib.auth import get_user_model

from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api

from modules.tramites.domain.models import Expediente, Solicitud
from modules.asignaciones.domain.models import Notificacion, NotificacionUsuario
from modules.asignaciones.domain.constants import TipoNotificacion, EstadoNotificacion
from modules.usuarios.domain.models import Area


@pytest.fixture
def usuario_notif(db):
    """Create a test user for Notificacion tests."""
    User = get_user_model()
    return User.objects.create_user(
        username="operador_notif",
        email="operador_notif@cip.gob.pe",
        password="testpass123",
        dni="99887766",
        nombres="Notificacion",
        apellidos="Operator",
    )


@pytest.fixture
def area_notif(db):
    """Create a test area."""
    return Area.objects.create(nombre="Área de Notificación", descripcion="Área para tests", activo=True)


def _make_auth_client(user):
    """Create a ninja_extra TestClient with JWT auth for the given user."""
    client = TestClient(api)
    token = AccessToken.for_user(user)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = user
    return client


def _crear_expediente_simple(usuario, numero, **kwargs):
    """Create an Expediente row directly."""
    defaults = dict(
        numero=numero,
        tipo_persona="NATURAL",
        dni="12345678",
        nombres="Juan",
        apellidos="Perez",
        correo="juan@test.com",
        telefono="999888777",
        tipo_documento="SOLICITUD",
        numero_documento=f"DOC-NOTIF-{numero:03d}",
        numero_folios=5,
        asunto=f"Trámite de notificación {numero}",
        fecha_registro=datetime.now(),
        creado_por=usuario,
    )
    defaults.update(kwargs)
    return Expediente.objects.create(**defaults)


def _crear_solicitud_simple(expediente, usuario, **kwargs):
    """Create a Solicitud row directly."""
    from modules.tramites.domain.constants import EstadoSolicitud, Prioridad
    defaults = dict(
        expediente=expediente,
        estado=EstadoSolicitud.EN_GESTION,
        prioridad=Prioridad.MEDIA,
        fecha_registro=datetime.now(),
        creado_por=usuario,
    )
    defaults.update(kwargs)
    return Solicitud.objects.create(**defaults)


# ── GET /notificaciones ───────────────────────────────────────────────────


@pytest.mark.django_db
def test_listar_notificaciones_vacio(usuario_notif):
    """
    GIVEN:  no notificaciones exist for the user and an authenticated user
    WHEN:   GET /notificaciones is called
    THEN:   response status is 200
            AND items is empty
            AND total is 0
    """
    client = _make_auth_client(usuario_notif)
    response = client.get("/notificaciones/")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.django_db
def test_listar_notificaciones_usuario(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion exists for the user (via NotificacionUsuario)
    WHEN:   GET /notificaciones is called
    THEN:   response status is 200
            AND the notification is returned
            AND interactuada reflects user's interaction
    """
    # Create a solicitud and notificacion
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Nueva asignación",
        mensaje="Se le ha asignado una nueva solicitud",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
    )

    # Link user to notification
    NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )

    client = _make_auth_client(usuario_notif)
    response = client.get("/notificaciones/")

    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["titulo"] == "Nueva asignación"
    assert item["tipo"] == "NUEVA_ASIGNACION"
    assert item["area_nombre"] == "Área de Notificación"


@pytest.mark.django_db
def test_listar_notificaciones_interactuada(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion where the user has marked it as vista
    WHEN:   GET /notificaciones is called
    THEN:   interactuada is True and vista is True
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Notificación vista",
        mensaje="Esta notificación fue vista",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
    )

    nu = NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )
    nu.vista_at = datetime.now()
    nu.save()

    client = _make_auth_client(usuario_notif)
    response = client.get("/notificaciones/")

    assert response.status_code == 200

    data = response.json()["data"]
    item = data["items"][0]
    assert item["vista"] is True
    assert item["interactuada"] is True


@pytest.mark.django_db
def test_listar_notificaciones_paginacion(usuario_notif, area_notif):
    """
    GIVEN:  5 notificaciones exist for the user
    WHEN:   GET /notificaciones?page=1&page_size=2 is called
    THEN:   response status is 200
            AND 2 items are returned
            AND total is 5
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    for i in range(5):
        notif = Notificacion.objects.create(
            area=area_notif,
            tipo=TipoNotificacion.NUEVA_ASIGNACION,
            solicitud=sol,
            titulo=f"Notificación {i}",
            mensaje=f"Mensaje {i}",
            estado=EstadoNotificacion.PENDIENTE,
            fecha_evento=datetime.now(),
        )
        NotificacionUsuario.objects.create(
            notificacion=notif,
            usuario=usuario_notif,
        )

    client = _make_auth_client(usuario_notif)
    response = client.get("/notificaciones/", {"page": 1, "page_size": 2})

    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 3


@pytest.mark.django_db
def test_listar_notificaciones_solo_usuario(usuario_notif, area_notif):
    """
    GIVEN:  two notificaciones exist for different users
    WHEN:   GET /notificaciones is called by one user
    THEN:   only notifications for that user are returned
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    otro_usuario = User.objects.create_user(
        username="otro_usuario",
        email="otro@cip.gob.pe",
        password="testpass123",
        dni="11223344",
        nombres="Otro",
        apellidos="Usuario",
    )

    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    # Notification for main user
    notif1 = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Para usuario 1",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
    )
    NotificacionUsuario.objects.create(notificacion=notif1, usuario=usuario_notif)

    # Notification for other user
    notif2 = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Para usuario 2",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
    )
    NotificacionUsuario.objects.create(notificacion=notif2, usuario=otro_usuario)

    client = _make_auth_client(usuario_notif)
    response = client.get("/notificaciones/")

    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["items"]) == 1
    assert data["items"][0]["titulo"] == "Para usuario 1"


# ── GET /notificaciones/{id} ───────────────────────────────────────────


@pytest.mark.django_db
def test_detalle_notificacion_no_existe(usuario_notif):
    """
    GIVEN:  no notificacion exists with the given ID
    WHEN:   GET /notificaciones/{id_fake} is called
    THEN:   response status is 404
    """
    import uuid
    fake_id = uuid.uuid4()

    client = _make_auth_client(usuario_notif)
    response = client.get(f"/notificaciones/{fake_id}")

    assert response.status_code == 404


@pytest.mark.django_db
def test_detalle_notificacion_basic(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion exists for the user
    WHEN:   GET /notificaciones/{id} is called
    THEN:   response status is 200
            AND includes all notification fields
            AND includes area info and contexto
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1, asunto="Trámite detalle")
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Detalle notificación",
        mensaje="Mensaje de prueba",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
        generada_por=usuario_notif,
    )

    NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )

    client = _make_auth_client(usuario_notif)
    response = client.get(f"/notificaciones/{notificacion.id}")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["id"] == str(notificacion.id)
    assert data["titulo"] == "Detalle notificación"
    assert data["mensaje"] == "Mensaje de prueba"
    assert data["tipo"] == "NUEVA_ASIGNACION"
    assert data["estado"] == "PENDIENTE"
    assert data["area_nombre"] == "Área de Notificación"
    assert "expediente_id_publico" in data
    assert data["expediente_asunto"] == "Trámite detalle"


@pytest.mark.django_db
def test_detalle_notificacion_interacciones(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion exists with user interactions
    WHEN:   GET /notificaciones/{id} is called
    THEN:   response includes the user's interactions
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Notificación con interacciones",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
    )

    nu = NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )
    nu.vista_at = datetime.now()
    nu.save()

    client = _make_auth_client(usuario_notif)
    response = client.get(f"/notificaciones/{notificacion.id}")

    assert response.status_code == 200

    data = response.json()["data"]
    assert "interacciones" in data
    assert len(data["interacciones"]) == 1
    assert data["interacciones"][0]["vista_at"] is not None


# ── POST /notificaciones/{id}/abrir ────────────────────────────────────────


@pytest.mark.django_db
def test_abrir_notificacion_no_existe(usuario_notif):
    """
    GIVEN:  no notificacion exists with the given ID
    WHEN:   POST /notificaciones/{id}/abrir is called
    THEN:   response status is 404
    """
    import uuid
    fake_id = uuid.uuid4()

    client = _make_auth_client(usuario_notif)
    response = client.post(f"/notificaciones/{fake_id}/abrir")

    assert response.status_code == 404


@pytest.mark.django_db
def test_abrir_notificacion_existe(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion exists for the user
    WHEN:   POST /notificaciones/{id}/abrir is called
    THEN:   response status is 200
            AND the notification detail is returned
            AND the user's interaction shows abierta_at is set
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Notificación por abrir",
        mensaje="Marcar como abierta",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
    )

    NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )

    client = _make_auth_client(usuario_notif)
    response = client.post(f"/notificaciones/{notificacion.id}/abrir")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["id"] == str(notificacion.id)
    assert data["titulo"] == "Notificación por abrir"
    # Verify the interaction was set
    assert len(data["interacciones"]) == 1
    assert data["interacciones"][0]["abierta_at"] is not None


@pytest.mark.django_db
def test_abrir_es_idempotente(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion exists where the user already marked it as abierta
    WHEN:   POST /notificaciones/{id}/abrir is called twice
    THEN:   response status is 200 on both calls
            AND abierta_at timestamp is preserved from the first call (not overwritten)
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Notificación ya abierta",
        mensaje="Verificación de idempotencia",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
    )

    nu = NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )
    nu.abierta_at = datetime.now()
    nu.save()

    client = _make_auth_client(usuario_notif)

    # First call
    response1 = client.post(f"/notificaciones/{notificacion.id}/abrir")
    assert response1.status_code == 200
    data1 = response1.json()["data"]
    abierta_at_1 = data1["interacciones"][0]["abierta_at"]

    # Second call (idempotent)
    response2 = client.post(f"/notificaciones/{notificacion.id}/abrir")
    assert response2.status_code == 200
    data2 = response2.json()["data"]
    abierta_at_2 = data2["interacciones"][0]["abierta_at"]

    # Timestamp should be the same (not overwritten)
    assert abierta_at_1 == abierta_at_2


@pytest.mark.django_db
def test_abrir_sin_autenticacion(area_notif):
    """
    GIVEN:  one notificacion exists for a user
    WHEN:   POST /notificaciones/{id}/abrir is called without authentication
    THEN:   response status is 401 or 403
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    system_user = User.objects.create_user(
        username="system_abrir",
        email="system_abrir@cip.gob.pe",
        password="testpass123",
        dni="00000003",
        nombres="System",
        apellidos="Abrir",
    )

    exp = _crear_expediente_simple(system_user, numero=1)
    sol = _crear_solicitud_simple(exp, system_user)

    notificacion = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Notificación sin auth",
        mensaje="Test auth",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
    )

    NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=system_user,
    )

    # Use an unauthenticated client (no Bearer token)
    client = TestClient(api)
    response = client.post(f"/notificaciones/{notificacion.id}/abrir")

    assert response.status_code in (401, 403)


# ── POST /notificaciones/{id}/descartar ────────────────────────────────────


@pytest.mark.django_db
def test_descartar_notificacion_no_existe(usuario_notif):
    """
    GIVEN:  no notificacion exists with the given ID
    WHEN:   POST /notificaciones/{id}/descartar is called
    THEN:   response status is 404
    """
    import uuid
    fake_id = uuid.uuid4()

    client = _make_auth_client(usuario_notif)
    response = client.post(f"/notificaciones/{fake_id}/descartar")

    assert response.status_code == 404


@pytest.mark.django_db
def test_descartar_notificacion_existe(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion exists for the user
    WHEN:   POST /notificaciones/{id}/descartar is called
    THEN:   response status is 200
            AND the notification detail is returned
            AND the user's interaction shows descartada_at is set
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Notificación por descartar",
        mensaje="Marcar como descartada",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
    )

    NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )

    client = _make_auth_client(usuario_notif)
    response = client.post(f"/notificaciones/{notificacion.id}/descartar")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["id"] == str(notificacion.id)
    assert data["titulo"] == "Notificación por descartar"
    # Verify the interaction was set
    assert len(data["interacciones"]) == 1
    assert data["interacciones"][0]["descartada_at"] is not None


@pytest.mark.django_db
def test_descartar_es_idempotente(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion exists where the user already marked it as descartada
    WHEN:   POST /notificaciones/{id}/descartar is called twice
    THEN:   response status is 200 on both calls
            AND descartada_at timestamp is preserved from the first call (not overwritten)
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Notificación ya descartada",
        mensaje="Verificación de idempotencia",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
    )

    nu = NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )
    nu.descartada_at = datetime.now()
    nu.save()

    client = _make_auth_client(usuario_notif)

    # First call
    response1 = client.post(f"/notificaciones/{notificacion.id}/descartar")
    assert response1.status_code == 200
    data1 = response1.json()["data"]
    descartada_at_1 = data1["interacciones"][0]["descartada_at"]

    # Second call (idempotent)
    response2 = client.post(f"/notificaciones/{notificacion.id}/descartar")
    assert response2.status_code == 200
    data2 = response2.json()["data"]
    descartada_at_2 = data2["interacciones"][0]["descartada_at"]

    # Timestamp should be the same (not overwritten)
    assert descartada_at_1 == descartada_at_2


@pytest.mark.django_db
def test_descartar_sin_autenticacion(area_notif):
    """
    GIVEN:  one notificacion exists for a user
    WHEN:   POST /notificaciones/{id}/descartar is called without authentication
    THEN:   response status is 401 or 403
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    system_user = User.objects.create_user(
        username="system_descartar",
        email="system_descartar@cip.gob.pe",
        password="testpass123",
        dni="00000004",
        nombres="System",
        apellidos="Descartar",
    )

    exp = _crear_expediente_simple(system_user, numero=1)
    sol = _crear_solicitud_simple(exp, system_user)

    notificacion = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Notificación sin auth",
        mensaje="Test auth",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
    )

    NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=system_user,
    )

    # Use an unauthenticated client (no Bearer token)
    client = TestClient(api)
    response = client.post(f"/notificaciones/{notificacion.id}/descartar")

    assert response.status_code in (401, 403)


# ── POST /notificaciones/{id}/vista ───────────────────────────────────────


@pytest.mark.django_db
def test_marcar_vista_notificacion_no_existe(usuario_notif):
    """
    GIVEN:  no notificacion exists with the given ID
    WHEN:   POST /notificaciones/{id}/vista is called
    THEN:   response status is 404
    """
    import uuid
    fake_id = uuid.uuid4()

    client = _make_auth_client(usuario_notif)
    response = client.post(f"/notificaciones/{fake_id}/vista")

    assert response.status_code == 404


@pytest.mark.django_db
def test_marcar_vista_notificacion_existe(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion exists for the user
    WHEN:   POST /notificaciones/{id}/vista is called
    THEN:   response status is 200
            AND the notification detail is returned
            AND the user's interaction shows vista_at is set
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Notificación por ver",
        mensaje="Marcar como vista",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
    )

    NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )

    client = _make_auth_client(usuario_notif)
    response = client.post(f"/notificaciones/{notificacion.id}/vista")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["id"] == str(notificacion.id)
    assert data["titulo"] == "Notificación por ver"
    # Verify the interaction was set
    assert len(data["interacciones"]) == 1
    assert data["interacciones"][0]["vista_at"] is not None


@pytest.mark.django_db
def test_marcar_vista_es_idempotente(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion exists where the user already marked it as vista
    WHEN:   POST /notificaciones/{id}/vista is called twice
    THEN:   response status is 200 on both calls
            AND vista_at timestamp is preserved from the first call (not overwritten)
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Notificación ya vista",
        mensaje="Verificación de idempotencia",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
    )

    nu = NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )
    nu.vista_at = datetime.now()
    nu.save()

    client = _make_auth_client(usuario_notif)

    # First call
    response1 = client.post(f"/notificaciones/{notificacion.id}/vista")
    assert response1.status_code == 200
    data1 = response1.json()["data"]
    vista_at_1 = data1["interacciones"][0]["vista_at"]

    # Second call (idempotent)
    response2 = client.post(f"/notificaciones/{notificacion.id}/vista")
    assert response2.status_code == 200
    data2 = response2.json()["data"]
    vista_at_2 = data2["interacciones"][0]["vista_at"]

    # Timestamp should be the same (not overwritten)
    assert vista_at_1 == vista_at_2


@pytest.mark.django_db
def test_marcar_vista_sin_autenticacion(area_notif):
    """
    GIVEN:  one notificacion exists for a user
    WHEN:   POST /notificaciones/{id}/vista is called without authentication
    THEN:   response status is 401 or 403
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    system_user = User.objects.create_user(
        username="system_vista",
        email="system_vista@cip.gob.pe",
        password="testpass123",
        dni="00000002",
        nombres="System",
        apellidos="Vista",
    )

    exp = _crear_expediente_simple(system_user, numero=1)
    sol = _crear_solicitud_simple(exp, system_user)

    notificacion = Notificacion.objects.create(
        area=area_notif,
        tipo=TipoNotificacion.NUEVA_ASIGNACION,
        solicitud=sol,
        titulo="Notificación sin auth",
        mensaje="Test auth",
        estado=EstadoNotificacion.PENDIENTE,
        fecha_evento=datetime.now(),
    )

    NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=system_user,
    )

    # Use an unauthenticated client (no Bearer token)
    client = TestClient(api)
    response = client.post(f"/notificaciones/{notificacion.id}/vista")

    assert response.status_code in (401, 403)
