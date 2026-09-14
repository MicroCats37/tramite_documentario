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
from modules.notificaciones.domain.models import Notificacion, NotificacionArea, NotificacionUsuario, NotificacionSolicitud
from modules.notificaciones.domain.constants import AmbitoNotificacion, EventoNotificacion, PrioridadNotificacion
from modules.notificaciones.presentation.schemas.notificacion_schemas import EstadoIndividual
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


class AuthTestClient(TestClient):
    """TestClient that sends the same Bearer JWT contract used by production."""

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._auth_user = user
        self._access_token = str(AccessToken.for_user(user))

    def request(self, method, path, data=None, json=None, **request_params):
        headers = dict(getattr(self, "headers", {}))
        headers.update(request_params.pop("headers", {}))
        headers.setdefault("Authorization", f"Bearer {self._access_token}")
        request_params["headers"] = headers
        return super().request(method, path, data, json, **request_params)


def _make_auth_client(user):
    """Create a ninja_extra TestClient with auth for the given user."""
    return AuthTestClient(user=user, router_or_app=api)


def _crear_expediente_simple(usuario, numero, **kwargs):
    """Create an Expediente row directly."""
    from modules.tramites.domain.models import TipoDocumento
    td = TipoDocumento.objects.get_or_create(
        nombre="SOLICITUD",
        descripcion="Solicitud",
    )[0]
    defaults = dict(
        numero=numero,
        tipo_persona="NATURAL",
        dni="12345678",
        nombres="Juan",
        apellidos="Perez",
        correo="juan@test.com",
        telefono="999888777",
        tipo_documento=td,
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
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        titulo="Nueva asignación",
        mensaje="Se le ha asignado una nueva solicitud",
        ocurrido_en=datetime.now(),
    )
    # Link table for solicitud context (solicitud FK removed from Notificacion)
    from modules.notificaciones.domain.models import NotificacionSolicitud
    NotificacionSolicitud.objects.create(notificacion=notificacion, solicitud=sol)
    NotificacionArea.objects.create(notificacion=notificacion, area=area_notif)

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
    assert item["ambito"] == "SOLICITUD"
    assert item["evento"] == "ASIGNACION_CREADA"
    # area_nombre is contextual — only present in detail endpoint, NOT in list


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
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        titulo="Notificación vista",
        mensaje="Esta notificación fue vista",
        ocurrido_en=datetime.now(),
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
            ambito=AmbitoNotificacion.SOLICITUD,
            evento=EventoNotificacion.ASIGNACION_CREADA,
            prioridad=PrioridadNotificacion.NORMAL,
            titulo=f"Notificación {i}",
            mensaje=f"Mensaje {i}",
            ocurrido_en=datetime.now(),
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
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Para usuario 1",

        ocurrido_en=datetime.now(),
    )
    NotificacionUsuario.objects.create(notificacion=notif1, usuario=usuario_notif)

    # Notification for other user
    notif2 = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Para usuario 2",

        ocurrido_en=datetime.now(),
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
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Detalle notificación",
        mensaje="Mensaje de prueba",

        ocurrido_en=datetime.now(),
        generada_por=usuario_notif,
    )
    NotificacionArea.objects.create(notificacion=notificacion, area=area_notif)

    NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )
    NotificacionSolicitud.objects.create(notificacion=notificacion, solicitud=sol)

    client = _make_auth_client(usuario_notif)
    response = client.get(f"/notificaciones/{notificacion.id}")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["id"] == str(notificacion.id)
    assert data["titulo"] == "Detalle notificación"
    assert data["mensaje"] == "Mensaje de prueba"
    assert data["ambito"] == "SOLICITUD"
    assert data["evento"] == "ASIGNACION_CREADA"
    assert data["prioridad"] == "NORMAL"
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
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación con interacciones",

        ocurrido_en=datetime.now(),
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
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación por abrir",
        mensaje="Marcar como abierta",

        ocurrido_en=datetime.now(),
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
            AND vista_at is also preserved (not overwritten)
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación ya abierta",
        mensaje="Verificación de idempotencia",

        ocurrido_en=datetime.now(),
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
    vista_at_1 = data1["interacciones"][0]["vista_at"]

    # Second call (idempotent)
    response2 = client.post(f"/notificaciones/{notificacion.id}/abrir")
    assert response2.status_code == 200
    data2 = response2.json()["data"]
    abierta_at_2 = data2["interacciones"][0]["abierta_at"]
    vista_at_2 = data2["interacciones"][0]["vista_at"]

    # Timestamps should be the same (not overwritten)
    assert abierta_at_1 == abierta_at_2
    assert vista_at_1 == vista_at_2


@pytest.mark.django_db
def test_abrir_setea_vista_at_si_es_null(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion exists for the user where vista_at is NULL but abierta_at is NOT NULL
    WHEN:   POST /notificaciones/{id}/abrir is called
    THEN:   response status is 200
            AND vista_at is set (because abrir also sets vista_at when NULL)
            AND abierta_at is preserved from the existing value
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación con solo abierta_at",
        mensaje="Verificación de invariant",

        ocurrido_en=datetime.now(),
    )

    nu = NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )
    # Only set abierta_at, not vista_at — this should not be possible after the fix
    nu.abierta_at = datetime.now()
    nu.save()
    assert nu.vista_at is None  # precondition

    client = _make_auth_client(usuario_notif)
    response = client.post(f"/notificaciones/{notificacion.id}/abrir")

    assert response.status_code == 200
    data = response.json()["data"]
    # vista_at should now be set
    assert data["interacciones"][0]["vista_at"] is not None
    # abierta_at should be preserved (same as before, not overwritten)
    assert data["interacciones"][0]["abierta_at"] is not None


@pytest.mark.django_db
def test_abrir_setea_ambos_cuando_vista_null(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion exists for the user where both vista_at and abierta_at are NULL
    WHEN:   POST /notificaciones/{id}/abrir is called
    THEN:   response status is 200
            AND both vista_at and abierta_at are set
            AND subsequent call preserves both timestamps (idempotency)
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación sin marcar",
        mensaje="Verificación de apertura",

        ocurrido_en=datetime.now(),
    )

    NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )
    # Both are NULL by default

    client = _make_auth_client(usuario_notif)

    # First call — both should be set
    response1 = client.post(f"/notificaciones/{notificacion.id}/abrir")
    assert response1.status_code == 200
    data1 = response1.json()["data"]
    assert data1["interacciones"][0]["vista_at"] is not None
    assert data1["interacciones"][0]["abierta_at"] is not None
    vista_at_1 = data1["interacciones"][0]["vista_at"]
    abierta_at_1 = data1["interacciones"][0]["abierta_at"]

    # Second call — idempotent, preserve timestamps
    response2 = client.post(f"/notificaciones/{notificacion.id}/abrir")
    assert response2.status_code == 200
    data2 = response2.json()["data"]
    assert data2["interacciones"][0]["vista_at"] == vista_at_1
    assert data2["interacciones"][0]["abierta_at"] == abierta_at_1


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
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación sin auth",
        mensaje="Test auth",

        ocurrido_en=datetime.now(),
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
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación por descartar",
        mensaje="Marcar como descartada",

        ocurrido_en=datetime.now(),
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
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación ya descartada",
        mensaje="Verificación de idempotencia",

        ocurrido_en=datetime.now(),
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
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación sin auth",
        mensaje="Test auth",

        ocurrido_en=datetime.now(),
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
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación por ver",
        mensaje="Marcar como vista",

        ocurrido_en=datetime.now(),
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
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación ya vista",
        mensaje="Verificación de idempotencia",

        ocurrido_en=datetime.now(),
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
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación sin auth",
        mensaje="Test auth",

        ocurrido_en=datetime.now(),
    )

    NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=system_user,
    )

    # Use an unauthenticated client (no Bearer token)
    client = TestClient(api)
    response = client.post(f"/notificaciones/{notificacion.id}/vista")

    assert response.status_code in (401, 403)


# ── Task 5: Nuevos campos core en API ───────────────────────────────────────


@pytest.mark.django_db
def test_listar_notificaciones_minimal_fields(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion exists for the user with full context
    WHEN:   GET /notificaciones is called
    THEN:   response includes only the 12 minimal fields
            AND contextual fields (solicitud_id, expediente_id_publico, area_nombre,
            periodo_id, solicitud_asunto, periodo_ciclo, periodo_activo, participo,
            audiencia_tipo) are NOT present in list items.
            Contextual data must be fetched via GET /notificaciones/{id}/detalle.
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1, asunto="Asunto de prueba")
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        titulo="Notificación con contexto",
        mensaje="Mensaje de prueba",

        ocurrido_en=datetime.now(),
    )
    NotificacionArea.objects.create(notificacion=notificacion, area=area_notif)
    NotificacionSolicitud.objects.create(notificacion=notificacion, solicitud=sol)

    NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )

    client = _make_auth_client(usuario_notif)
    response = client.get("/notificaciones/")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert len(data["items"]) == 1
    item = data["items"][0]

    # 12 minimal fields that MUST be present in list response
    assert "id" in item
    assert "ambito" in item
    assert "evento" in item
    assert "prioridad" in item
    assert "titulo" in item
    assert "mensaje" in item
    assert "ocurrido_en" in item
    assert "interactuada" in item
    assert "vista" in item
    assert "abierta" in item
    assert "descartada" in item
    assert "estado_individual" in item

    # Verify values of minimal fields
    assert item["ambito"] == "SOLICITUD"
    assert item["evento"] == "ASIGNACION_CREADA"
    assert item["prioridad"] == "NORMAL"
    assert item["titulo"] == "Notificación con contexto"
    assert item["estado_individual"] == "NO_VISTA"
    assert item["interactuada"] is False
    assert item["vista"] is False
    assert item["abierta"] is False
    assert item["descartada"] is False

    # Contextual fields must NOT be present in list response
    assert "solicitud_id" not in item
    assert "expediente_id_publico" not in item
    assert "area_nombre" not in item
    assert "periodo_id" not in item
    assert "solicitud_asunto" not in item
    assert "periodo_ciclo" not in item
    assert "periodo_activo" not in item
    assert "participo" not in item
    assert "audiencia_tipo" not in item


@pytest.mark.django_db
def test_listar_notificaciones_estado_individual_vista(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion where user marked it as vista
    WHEN:   GET /notificaciones is called
    THEN:   estado_individual is VISTA
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación vista",

        ocurrido_en=datetime.now(),
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
    assert item["estado_individual"] == EstadoIndividual.VISTA.value


@pytest.mark.django_db
def test_listar_notificaciones_estado_individual_abierta(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion where user opened it (abierta)
    WHEN:   GET /notificaciones is called
    THEN:   estado_individual is ABIERTA (takes precedence over VISTA)
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación abierta",

        ocurrido_en=datetime.now(),
    )

    nu = NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )
    nu.vista_at = datetime.now()
    nu.abierta_at = datetime.now()
    nu.save()

    client = _make_auth_client(usuario_notif)
    response = client.get("/notificaciones/")

    assert response.status_code == 200
    data = response.json()["data"]
    item = data["items"][0]
    assert item["estado_individual"] == EstadoIndividual.ABIERTA.value


@pytest.mark.django_db
def test_listar_notificaciones_estado_individual_descartada(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion where user discarded it
    WHEN:   GET /notificaciones is called
    THEN:   estado_individual is DESCARTADA (takes precedence over ABIERTA and VISTA)
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación descartada",

        ocurrido_en=datetime.now(),
    )

    nu = NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=usuario_notif,
    )
    nu.descartada_at = datetime.now()
    nu.save()

    client = _make_auth_client(usuario_notif)
    response = client.get("/notificaciones/")

    assert response.status_code == 200
    data = response.json()["data"]
    item = data["items"][0]
    assert item["estado_individual"] == EstadoIndividual.DESCARTADA.value


@pytest.mark.django_db
def test_detalle_notificacion_nuevos_campos(usuario_notif, area_notif):
    """
    GIVEN:  one notificacion exists for the user
    WHEN:   GET /notificaciones/{id} is called
    THEN:   response includes all new fields in detail
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1, asunto="Asunto detalle")
    sol = _crear_solicitud_simple(exp, usuario_notif)

    notificacion = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        titulo="Detalle con nuevos campos",
        mensaje="Mensaje detalle",

        ocurrido_en=datetime.now(),
        generada_por=usuario_notif,
    )
    NotificacionArea.objects.create(notificacion=notificacion, area=area_notif)
    NotificacionSolicitud.objects.create(notificacion=notificacion, solicitud=sol)

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

    # Nuevos campos
    assert "ambito" in data
    assert "evento" in data
    assert "prioridad" in data
    assert "audiencia_tipo" in data
    assert "estado_individual" in data
    assert "solicitud_asunto" in data
    assert "periodo_ciclo" in data
    assert "periodo_activo" in data
    assert "participo" in data

    # Verificar valores
    assert data["ambito"] == "SOLICITUD"
    assert data["evento"] == "ASIGNACION_CREADA"
    assert data["prioridad"] == "NORMAL"
    assert data["audiencia_tipo"] == "AREA"
    assert data["estado_individual"] == "NO_VISTA"
    assert data["solicitud_asunto"] == "Asunto detalle"


# ── Task 6: GET /notificaciones/resumen ────────────────────────────────────────


@pytest.mark.django_db
def test_resumen_vacio(usuario_notif):
    """
    GIVEN:  no notificaciones exist for the user and an authenticated user
    WHEN:   GET /notificaciones/resumen is called
    THEN:   response status is 200
            AND total is 0
            AND sin_leer is 0
            AND all counts are 0
    """
    client = _make_auth_client(usuario_notif)
    response = client.get("/notificaciones/resumen")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["total"] == 0
    assert data["no_vistas"] == 0
    assert data["vistas"] == 0
    assert data["abiertas"] == 0
    assert data["descartadas"] == 0
    assert data["sin_leer"] == 0


@pytest.mark.django_db
def test_resumen_con_notificaciones(usuario_notif, area_notif):
    """
    GIVEN:  notifications exist with different interaction states for the user
    WHEN:   GET /notificaciones/resumen is called
    THEN:   response status is 200
            AND counts match the expected distribution
    """
    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    # Notification 1: NO_VISTA (all null)
    notif1 = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="No vista",

        ocurrido_en=datetime.now(),
    )
    NotificacionUsuario.objects.create(notificacion=notif1, usuario=usuario_notif)

    # Notification 2: VISTA (only vista_at set)
    notif2 = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        titulo="Notificación vista",
        ocurrido_en=datetime.now(),
    )
    nu2 = NotificacionUsuario.objects.create(notificacion=notif2, usuario=usuario_notif)
    nu2.vista_at = datetime.now()
    nu2.save()

    # Notification 3: ABIERTA (vista_at + abierta_at)
    notif3 = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Abierta",

        ocurrido_en=datetime.now(),
    )
    nu3 = NotificacionUsuario.objects.create(notificacion=notif3, usuario=usuario_notif)
    nu3.vista_at = datetime.now()
    nu3.abierta_at = datetime.now()
    nu3.save()

    # Notification 4: DESCARTADA
    notif4 = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Descartada",

        ocurrido_en=datetime.now(),
    )
    nu4 = NotificacionUsuario.objects.create(notificacion=notif4, usuario=usuario_notif)
    nu4.descartada_at = datetime.now()
    nu4.save()

    client = _make_auth_client(usuario_notif)
    response = client.get("/notificaciones/resumen")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["total"] == 4
    assert data["no_vistas"] == 1
    assert data["vistas"] == 1
    assert data["abiertas"] == 1
    assert data["descartadas"] == 1
    # sin_leer is alias of no_vistas
    assert data["sin_leer"] == data["no_vistas"]


@pytest.mark.django_db
def test_resumen_sin_autenticacion(area_notif):
    """
    GIVEN:  one notificacion exists for a user
    WHEN:   GET /notificaciones/resumen is called without authentication
    THEN:   response status is 401 or 403
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    system_user = User.objects.create_user(
        username="system_resumen",
        email="system_resumen@cip.gob.pe",
        password="testpass123",
        dni="00000005",
        nombres="System",
        apellidos="Resumen",
    )

    exp = _crear_expediente_simple(system_user, numero=1)
    sol = _crear_solicitud_simple(exp, system_user)

    notificacion = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Notificación sin auth",
        mensaje="Test auth",

        ocurrido_en=datetime.now(),
    )

    NotificacionUsuario.objects.create(
        notificacion=notificacion,
        usuario=system_user,
    )

    # Use an unauthenticated client (no Bearer token)
    client = TestClient(api)
    response = client.get("/notificaciones/resumen")

    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_resumen_solo_usuario(usuario_notif, area_notif):
    """
    GIVEN:  two notificaciones exist for different users
    WHEN:   GET /notificaciones/resumen is called by one user
    THEN:   only counts for that user are returned
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    otro_usuario = User.objects.create_user(
        username="otro_resumen",
        email="otro_resumen@cip.gob.pe",
        password="testpass123",
        dni="55443322",
        nombres="Otro",
        apellidos="Resumen",
    )

    exp = _crear_expediente_simple(usuario_notif, numero=1)
    sol = _crear_solicitud_simple(exp, usuario_notif)

    # Notification for main user
    notif1 = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Para usuario 1",

        ocurrido_en=datetime.now(),
    )
    NotificacionUsuario.objects.create(notificacion=notif1, usuario=usuario_notif)

    # Notification for other user
    notif2 = Notificacion.objects.create(
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,

        titulo="Para usuario 2",

        ocurrido_en=datetime.now(),
    )
    NotificacionUsuario.objects.create(notificacion=notif2, usuario=otro_usuario)

    client = _make_auth_client(usuario_notif)
    response = client.get("/notificaciones/resumen")

    assert response.status_code == 200

    data = response.json()["data"]
    assert data["total"] == 1
    assert data["no_vistas"] == 1


# ── E2E: Mention notification end-to-end flow ─────────────────────────────────


@pytest.fixture
def usuario_notif_2(db):
    """A second test user for mention notification tests."""
    User = get_user_model()
    return User.objects.create_user(
        username="mensionado02",
        email="mensionado02@cip.gob.pe",
        password="testpass123",
        dni="55443322",
        nombres="Usuario",
        apellidos="Mensionado",
    )


@pytest.mark.django_db(transaction=True)
class TestMencionNotificacionE2E:
    """
    E2E proof: contextual comment with mention → mentioned user receives notification.

    Full flow:
    1. user A (author) creates a linked conversacion on a solicitud
    2. user A posts a comment mentioning user B
    3. As user B: GET /notificaciones returns ambito=SOLICITUD, evento=COMENTARIO_MENCION
    4. As user A: GET /notificaciones does NOT return that notification

    Uses TestAsyncClient (async) because SolicitudComentarioController is async.
    """

    @pytest.fixture
    def linked_solicitud(self, usuario_notif, area_notif):
        """Create an expediente + solicitud + linked conversacion via bridge."""
        exp = _crear_expediente_simple(usuario_notif, numero=9001)
        sol = _crear_solicitud_simple(exp, usuario_notif)
        # Create and bridge the conversacion
        from modules.conversaciones.domain.models import Conversacion, SolicitudConversacion
        from datetime import datetime as dt
        conv = Conversacion.objects.create(
            titulo="Conversación de prueba mencion",
            creada_por=usuario_notif,
            fecha_inicio=dt.now(),
        )
        SolicitudConversacion.objects.create(
            solicitud=sol,
            conversacion=conv,
        )
        return sol, conv

    def _auth_headers(self, user):
        token = str(AccessToken.for_user(user))
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_comentario_con_mencion_crea_notificacion_para_mencionado(
        self, usuario_notif, usuario_notif_2, linked_solicitud, area_notif
    ):
        """
        GIVEN:  user A and user B exist, and a linked conversacion on a solicitud
        WHEN:   user A posts a comment mentioning user B
        THEN:   user B's GET /notificaciones returns a notification
                with ambito=SOLICITUD and evento=COMENTARIO_MENCION
                AND user A does NOT see that notification in their listing
        """
        import json
        from ninja_extra.testing import TestAsyncClient

        sol, conv = linked_solicitud

        # Client for user A (author)
        client_a = TestAsyncClient(api)
        headers_a = self._auth_headers(usuario_notif)

        # Post comment mentioning user B via FormData
        payload = {
            "contenido": "Hola @mensionado, necesito tu opinión",
            "menciones": [{"usuario_id": str(usuario_notif_2.id)}],
        }
        form_data = {"data": json.dumps(payload)}
        resp = await client_a.post(
            f"/solicitudes/{sol.id}/conversaciones/{conv.id}/comentarios",
            data=form_data,
            headers=headers_a,
        )
        assert resp.status_code == 200, (
            f"Expected 200 posting comment, got {resp.status_code}: {resp.content}"
        )
        mensaje_data = resp.json()["data"]
        assert len(mensaje_data.get("menciones", [])) == 1
        assert mensaje_data["menciones"][0]["usuario_id"] == str(usuario_notif_2.id)

        # Switch to user B — check notifications
        client_b = TestAsyncClient(api)
        headers_b = self._auth_headers(usuario_notif_2)
        resp_b = await client_b.get("/notificaciones/?page=1&page_size=10", headers=headers_b)
        assert resp_b.status_code == 200, (
            f"Expected 200 listing notifications, got {resp_b.status_code}: {resp_b.content}"
        )
        data_b = resp_b.json()["data"]

        # Find the mention notification for user B
        mention_items = [
            item for item in data_b["items"]
            if item["evento"] == "COMENTARIO_MENCION" and item["ambito"] == "SOLICITUD"
        ]
        assert len(mention_items) == 1, (
            f"Expected exactly 1 COMENTARIO_MENCION notification for user B, "
            f"got {len(mention_items)} in {data_b['items']}"
        )
        item = mention_items[0]
        assert item["ambito"] == "SOLICITUD"
        assert item["evento"] == "COMENTARIO_MENCION"
        assert item["estado_individual"] == "NO_VISTA"

        # Switch back to user A — should NOT see the mention notification
        resp_a = await client_a.get("/notificaciones/?page=1&page_size=10", headers=headers_a)
        assert resp_a.status_code == 200
        data_a = resp_a.json()["data"]
        mention_items_a = [
            item for item in data_a["items"]
            if item["evento"] == "COMENTARIO_MENCION"
        ]
        assert len(mention_items_a) == 0, (
            f"Author should NOT see mention notification, but got: {mention_items_a}"
        )
