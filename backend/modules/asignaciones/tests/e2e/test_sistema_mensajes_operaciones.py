"""
Focused tests for SISTEMA message creation on period operations.

Tests prove:
1. Period operations (tomar, finalizar, cambiar_participacion) each create
   exactly one Mensaje with tipo=SISTEMA, autor_usuario=None, containing
   area name, cycle number, and actor name.
2. Those operations create ZERO Notificacion and ZERO NotificacionUsuario rows.
3. Finalizar Solicitud creates a SISTEMA message with area/actor but NOT the
   formal response content; SolicitudRespuesta.contenido still has the full text.
"""
import json

import pytest
from datetime import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone

from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken

from config.api import api
from modules.tramites.domain.models import (
    Expediente,
    Solicitud,
    SolicitudEstadoHistorial,
    SolicitudRespuesta,
    TipoDocumento,
)
from modules.asignaciones.domain.models import (
    SolicitudAsignacion,
    SolicitudAsignacionPeriodo,
    SolicitudAsignacionPeriodoEstadoHistorial,
    SolicitudAsignacionUsuario,
)
from modules.asignaciones.domain.constants import (
    EstadoPeriodo,
    EstadoPeriodoOperativo,
    EstadoRespuesta,
    OrigenEstadoPeriodo,
    TipoCierre,
    TipoParticipacion,
)
from modules.conversaciones.domain.models import Conversacion, Mensaje, SolicitudConversacion
from modules.notificaciones.domain.models import Notificacion, NotificacionUsuario
from modules.usuarios.domain.models import Area
from modules.tramites.domain.models.solicitud_historial import OrigenCambio
from modules.tramites.domain.constants import EstadoSolicitud


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def usuario_operador(db):
    """Test user for period operations."""
    User = get_user_model()
    return User.objects.create_user(
        username="operador_sistema_msg",
        email="operador_sistema_msg@cip.gob.pe",
        password="testpass123",
        dni="11223344",
        nombres="Carlos",
        apellidos="Mendez",
    )


@pytest.fixture
def area_gestion(db):
    """Test area."""
    return Area.objects.create(
        nombre="Gestión de Trámites",
        descripcion="Área de gestión de trámites",
        activo=True,
    )


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_auth_client(user):
    """JWT-authenticated test client."""
    client = TestClient(api)
    token = AccessToken.for_user(user)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = user
    return client


def _get_or_create_tipo_doc_solicitud():
    """Get or create a SOLICITUD TipoDocumento, safe for all test DB states."""
    tipo_doc, _ = TipoDocumento.objects.get_or_create(
        nombre="SOLICITUD",
        defaults={"descripcion": "Tipo documento Solicitud"},
    )
    return tipo_doc


def _crear_solicitud_con_periodo_pendiente_y_conversacion(usuario, area):
    """
    Create a Solicitud in EN_GESTION with:
    - one Expediente (proper TipoDocumento instance)
    - one area assignment
    - one periodo in PENDIENTE state
    - a linked Conversacion via SolicitudConversacion bridge

    Returns (solicitud, asignacion, periodo, conversacion).
    """
    ahora = datetime.now()
    tipo_doc = _get_or_create_tipo_doc_solicitud()

    expediente = Expediente.objects.create(
        numero=500,
        tipo_persona="NATURAL",
        dni="11223355",
        nombres="Test",
        apellidos="User",
        correo="test500@example.com",
        telefono="900900500",
        tipo_documento=tipo_doc,
        numero_documento="DOC-2026-SM01-001",
        numero_folios=3,
        asunto="Trámite para prueba de mensajes de sistema",
        fecha_registro=ahora,
        creado_por=usuario,
    )

    solicitud = Solicitud.objects.create(
        expediente=expediente,
        estado="EN_GESTION",
        prioridad="MEDIA",
        fecha_registro=ahora,
        fecha_inicio_gestion=ahora,
        creado_por=usuario,
    )
    SolicitudEstadoHistorial.objects.create(
        solicitud=solicitud,
        estado_anterior=None,
        estado_nuevo="REGISTRADA",
        cambiado_por=usuario,
        fecha_cambio=ahora,
        origen="CREACION",
    )
    SolicitudEstadoHistorial.objects.create(
        solicitud=solicitud,
        estado_anterior="REGISTRADA",
        estado_nuevo="EN_GESTION",
        cambiado_por=usuario,
        fecha_cambio=ahora,
        origen="CAMBIO_ESTADO",
    )

    asignacion = SolicitudAsignacion.objects.create(
        solicitud=solicitud,
        area=area,
        fecha_incorporacion=ahora,
        incorporado_por=usuario,
    )

    periodo = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        tipo_participacion="PRINCIPAL",
        estado=EstadoPeriodo.PENDIENTE,
        fecha_inicio=ahora,
        iniciado_por=usuario,
    )
    SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
        periodo=periodo,
        estado_anterior=None,
        estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
        fecha_cambio=ahora,
        cambiado_por=usuario,
        origen=OrigenEstadoPeriodo.CREACION,
    )

    # Create conversation bridge so system messages can be created
    conversacion = Conversacion.objects.create(
        titulo=f"Conversación - {expediente.id_publico}",
        creada_por=usuario,
        fecha_inicio=ahora,
    )
    SolicitudConversacion.objects.create(
        solicitud=solicitud,
        conversacion=conversacion,
    )

    return solicitud, asignacion, periodo, conversacion


def _crear_solicitud_con_periodo_en_gestion_y_conversacion(usuario, area):
    """
    Same as above but periodo starts in EN_GESTION state (already taken).
    Returns (solicitud, asignacion, periodo, conversacion).
    """
    ahora = datetime.now()
    tipo_doc = _get_or_create_tipo_doc_solicitud()

    expediente = Expediente.objects.create(
        numero=501,
        tipo_persona="NATURAL",
        dni="11223366",
        nombres="Test",
        apellidos="User2",
        correo="test501@example.com",
        telefono="900900501",
        tipo_documento=tipo_doc,
        numero_documento="DOC-2026-SM01-002",
        numero_folios=3,
        asunto="Trámite para prueba de finalizar periodo",
        fecha_registro=ahora,
        creado_por=usuario,
    )

    solicitud = Solicitud.objects.create(
        expediente=expediente,
        estado="EN_GESTION",
        prioridad="ALTA",
        fecha_registro=ahora,
        fecha_inicio_gestion=ahora,
        creado_por=usuario,
    )
    SolicitudEstadoHistorial.objects.create(
        solicitud=solicitud,
        estado_anterior=None,
        estado_nuevo="REGISTRADA",
        cambiado_por=usuario,
        fecha_cambio=ahora,
        origen="CREACION",
    )
    SolicitudEstadoHistorial.objects.create(
        solicitud=solicitud,
        estado_anterior="REGISTRADA",
        estado_nuevo="EN_GESTION",
        cambiado_por=usuario,
        fecha_cambio=ahora,
        origen="CAMBIO_ESTADO",
    )

    asignacion = SolicitudAsignacion.objects.create(
        solicitud=solicitud,
        area=area,
        fecha_incorporacion=ahora,
        incorporado_por=usuario,
    )

    periodo = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        tipo_participacion="PRINCIPAL",
        estado=EstadoPeriodo.EN_GESTION,
        fecha_inicio=ahora,
        iniciado_por=usuario,
    )
    SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
        periodo=periodo,
        estado_anterior=None,
        estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
        fecha_cambio=ahora,
        cambiado_por=usuario,
        origen=OrigenEstadoPeriodo.CREACION,
    )
    SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
        periodo=periodo,
        estado_anterior=EstadoPeriodoOperativo.PENDIENTE,
        estado_nuevo=EstadoPeriodoOperativo.EN_GESTION,
        fecha_cambio=ahora,
        cambiado_por=usuario,
        origen=OrigenEstadoPeriodo.AUTOASIGNACION,
    )
    # Pre-assign the user as participant
    SolicitudAsignacionUsuario.objects.create(
        periodo=periodo,
        usuario=usuario,
        rol="Responsable",
        fecha_inicio=ahora,
        asignado_por=usuario,
    )

    conversacion = Conversacion.objects.create(
        titulo=f"Conversación - {expediente.id_publico}",
        creada_por=usuario,
        fecha_inicio=ahora,
    )
    SolicitudConversacion.objects.create(
        solicitud=solicitud,
        conversacion=conversacion,
    )

    return solicitud, asignacion, periodo, conversacion


# ── Test: tomar_periodo → SISTEMA Mensaje, NO Notificacion ────────────────

@pytest.mark.django_db(transaction=True)
def test_tomar_periodo_crea_mensaje_sistema_no_notificacion(
    usuario_operador, area_gestion
):
    """
    GIVEN: a SolicitudAsignacionPeriodo in PENDIENTE with a linked conversation
    WHEN:  POST /periodos/{id}/tomar is called
    THEN:  exactly ONE Mensaje is created with:
              - tipo = 'SISTEMA'
              - autor_usuario = None
              - contenido contains area name, cycle number '1', actor name 'Carlos Mendez'
            AND ZERO Notificacion rows are created
            AND ZERO NotificacionUsuario rows are created
    """
    solicitud, asignacion, periodo, conversacion = (
        _crear_solicitud_con_periodo_pendiente_y_conversacion(
            usuario_operador, area_gestion
        )
    )

    count_mensaje_before = Mensaje.objects.filter(conversacion=conversacion).count()
    count_notif_before = Notificacion.objects.count()
    count_notif_user_before = NotificacionUsuario.objects.count()

    client = _make_auth_client(usuario_operador)
    response = client.post(f"/periodos/{periodo.id}/tomar")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    count_mensaje_after = Mensaje.objects.filter(conversacion=conversacion).count()
    count_notif_after = Notificacion.objects.count()
    count_notif_user_after = NotificacionUsuario.objects.count()

    # One new Mensaje was created
    assert count_mensaje_after == count_mensaje_before + 1, (
        f"Expected +1 Mensaje, got {count_mensaje_after - count_mensaje_before}"
    )

    # Zero Notificacion rows created
    assert count_notif_after == count_notif_before, (
        f"Expected 0 new Notificacion, got {count_notif_after - count_notif_before}"
    )

    # Zero NotificacionUsuario rows created
    assert count_notif_user_after == count_notif_user_before, (
        f"Expected 0 new NotificacionUsuario, got {count_notif_user_after - count_notif_user_before}"
    )

    # Verify the Mensaje properties
    mensaje = (
        Mensaje.objects.filter(conversacion=conversacion)
        .order_by("-fecha_envio")
        .first()
    )
    assert mensaje.tipo == "SISTEMA", f"Expected tipo=SISTEMA, got {mensaje.tipo}"
    assert mensaje.autor_usuario_id is None, (
        f"Expected autor_usuario=None, got {mensaje.autor_usuario_id}"
    )
    assert area_gestion.nombre in mensaje.contenido, (
        f"Contenido should contain area name '{area_gestion.nombre}': {mensaje.contenido}"
    )
    assert "1" in mensaje.contenido, (
        f"Contenido should contain cycle '1': {mensaje.contenido}"
    )
    assert "Carlos Mendez" in mensaje.contenido, (
        f"Contenido should contain actor name 'Carlos Mendez': {mensaje.contenido}"
    )


# ── Test: finalizar_periodo → SISTEMA Mensaje, NO Notificacion ────────────

@pytest.mark.django_db(transaction=True)
def test_finalizar_periodo_crea_mensaje_sistema_no_notificacion(
    usuario_operador, area_gestion
):
    """
    GIVEN: a SolicitudAsignacionPeriodo in EN_GESTION with a linked conversation
    WHEN:  POST /periodos/{id}/finalizar is called
    THEN:  exactly ONE Mensaje is created with:
              - tipo = 'SISTEMA'
              - autor_usuario = None
              - contenido contains area name, cycle number '1', actor name 'Carlos Mendez'
            AND ZERO Notificacion rows are created
            AND ZERO NotificacionUsuario rows are created
    """
    solicitud, asignacion, periodo, conversacion = (
        _crear_solicitud_con_periodo_en_gestion_y_conversacion(
            usuario_operador, area_gestion
        )
    )

    count_mensaje_before = Mensaje.objects.filter(conversacion=conversacion).count()
    count_notif_before = Notificacion.objects.count()
    count_notif_user_before = NotificacionUsuario.objects.count()

    client = _make_auth_client(usuario_operador)
    response = client.post(f"/periodos/{periodo.id}/finalizar")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    count_mensaje_after = Mensaje.objects.filter(conversacion=conversacion).count()
    count_notif_after = Notificacion.objects.count()
    count_notif_user_after = NotificacionUsuario.objects.count()

    # One new Mensaje was created
    assert count_mensaje_after == count_mensaje_before + 1, (
        f"Expected +1 Mensaje, got {count_mensaje_after - count_mensaje_before}"
    )

    # Zero Notificacion rows created
    assert count_notif_after == count_notif_before, (
        f"Expected 0 new Notificacion, got {count_notif_after - count_notif_before}"
    )

    # Zero NotificacionUsuario rows created
    assert count_notif_user_after == count_notif_user_before, (
        f"Expected 0 new NotificacionUsuario, got {count_notif_user_after - count_notif_user_before}"
    )

    # Verify the Mensaje properties
    mensaje = (
        Mensaje.objects.filter(conversacion=conversacion)
        .order_by("-fecha_envio")
        .first()
    )
    assert mensaje.tipo == "SISTEMA", f"Expected tipo=SISTEMA, got {mensaje.tipo}"
    assert mensaje.autor_usuario_id is None
    assert area_gestion.nombre in mensaje.contenido
    assert "1" in mensaje.contenido
    assert "Carlos Mendez" in mensaje.contenido


# ── Test: cambiar_participacion → SISTEMA Mensaje, NO Notificacion ─────────

@pytest.mark.django_db(transaction=True)
def test_cambiar_participacion_crea_mensaje_sistema_no_notificacion(
    usuario_operador, area_gestion
):
    """
    GIVEN: a SolicitudAsignacionPeriodo in EN_GESTION (PRINCIPAL) with a linked conversation
    WHEN:  POST /periodos/{id}/cambiar-participacion is called with ADJUNTA
    THEN:  exactly ONE Mensaje is created with:
              - tipo = 'SISTEMA'
              - autor_usuario = None
              - contenido contains area name, cycle number '1', actor name, and 'ADJUNTA'
            AND ZERO Notificacion rows are created
            AND ZERO NotificacionUsuario rows are created
    """
    solicitud, asignacion, periodo, conversacion = (
        _crear_solicitud_con_periodo_en_gestion_y_conversacion(
            usuario_operador, area_gestion
        )
    )

    count_mensaje_before = Mensaje.objects.filter(conversacion=conversacion).count()
    count_notif_before = Notificacion.objects.count()
    count_notif_user_before = NotificacionUsuario.objects.count()

    client = _make_auth_client(usuario_operador)
    response = client.post(
        f"/periodos/{periodo.id}/cambiar-participacion",
        json={"tipo_participacion": "ADJUNTA"},
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    count_mensaje_after = Mensaje.objects.filter(conversacion=conversacion).count()
    count_notif_after = Notificacion.objects.count()
    count_notif_user_after = NotificacionUsuario.objects.count()

    # One new Mensaje was created
    assert count_mensaje_after == count_mensaje_before + 1, (
        f"Expected +1 Mensaje, got {count_mensaje_after - count_mensaje_before}"
    )

    # Zero Notificacion rows created
    assert count_notif_after == count_notif_before, (
        f"Expected 0 new Notificacion, got {count_notif_after - count_notif_before}"
    )

    # Zero NotificacionUsuario rows created
    assert count_notif_user_after == count_notif_user_before, (
        f"Expected 0 new NotificacionUsuario, got {count_notif_user_after - count_notif_user_before}"
    )

    # Verify the Mensaje properties
    mensaje = (
        Mensaje.objects.filter(conversacion=conversacion)
        .order_by("-fecha_envio")
        .first()
    )
    assert mensaje.tipo == "SISTEMA", f"Expected tipo=SISTEMA, got {mensaje.tipo}"
    assert mensaje.autor_usuario_id is None
    assert area_gestion.nombre in mensaje.contenido
    assert "1" in mensaje.contenido
    assert "Carlos Mendez" in mensaje.contenido
    assert "ADJUNTA" in mensaje.contenido, (
        f"Contenido should mention ADJUNTA: {mensaje.contenido}"
    )


# ── Test: finalizar solicitud → SISTEMA message without formal response ────

@pytest.mark.django_db(transaction=True)
def test_finalizar_solicitud_mensaje_sin_contenido_formal(
    usuario_operador, area_gestion
):
    """
    GIVEN: a Solicitud in EN_GESTION with a linked conversation
    WHEN:  POST /solicitudes/{id}/finalizar is called with tipo_respuesta + contenido
    THEN:  the SISTEMA message in the conversation:
              - contains the area name
              - contains the actor name
              - does NOT contain the formal response text "Informe secreto de cierre"
            AND SolicitudRespuesta.contenido == "Informe secreto de cierre"
              (full formal response is preserved separately)
    """
    from config.api import api as tramites_api

    # Re-use the helper from the integration test suite's pattern
    solicitud, asignacion, periodo, conversacion = (
        _crear_solicitud_con_periodo_en_gestion_y_conversacion(
            usuario_operador, area_gestion
        )
    )

    # The user's area is already inferred from SolicitudAsignacionUsuario participation
    # in _inferir_area_periodo, so no extra AsignacionUsuario needed.
    count_mensaje_before = Mensaje.objects.filter(conversacion=conversacion).count()

    client = _make_auth_client(usuario_operador)
    payload = {
        "tipo_respuesta": "INFORME",
        "contenido": "Informe secreto de cierre.",
        "es_final": "true",
    }

    response = client.post(
        f"/solicitudes/{solicitud.id}/finalizar",
        data={"data": json.dumps(payload)},
        files=[],
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    # One new Mensaje was created
    count_mensaje_after = Mensaje.objects.filter(conversacion=conversacion).count()
    assert count_mensaje_after == count_mensaje_before + 1

    # Find the SISTEMA mensaje (not the file attachment message)
    mensajes = (
        Mensaje.objects.filter(conversacion=conversacion)
        .order_by("-fecha_envio")
    )
    sistema_msgs = [m for m in mensajes if m.tipo == "SISTEMA"]
    assert len(sistema_msgs) >= 1, "At least one SISTEMA mensaje should exist"

    mensaje = sistema_msgs[0]
    contenido = mensaje.contenido

    # Message contains area and actor
    assert area_gestion.nombre in contenido, (
        f"Message should contain area name '{area_gestion.nombre}': {contenido}"
    )
    assert "Carlos Mendez" in contenido, (
        f"Message should contain actor name 'Carlos Mendez': {contenido}"
    )

    # Message does NOT contain the formal response content
    assert "Informe secreto de cierre" not in contenido, (
        f"Message should NOT contain formal response text: {contenido}"
    )

    # Verify SolicitudRespuesta still has the full formal response
    respuesta = SolicitudRespuesta.objects.filter(solicitud=solicitud).first()
    assert respuesta is not None, "SolicitudRespuesta should be created"
    assert respuesta.contenido == "Informe secreto de cierre.", (
        f"SolicitudRespuesta.contenido should preserve full formal response: {respuesta.contenido}"
    )
