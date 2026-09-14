"""
Integration tests for SolicitudRespuesta (finalizar endpoint).

Tests cover:
- FinalizarSolicitudIn endpoint: crear respuesta final exitosamente (con contenido)
- FinalizarSolicitudIn endpoint: crear respuesta final con cambio de estado a FINALIZADA
- Crear SolicitudRespuesta vinculada a Mensaje y Conversacion
- Duplicate final response (es_final=True) returns 409 Conflict
- Solicitud already FINALIZADA returns 409
- Solicitud already ANULADA returns 409
- Usuario sin area asignada returns 400
"""
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken

from modules.asignaciones.domain.constants import TipoParticipacion
from django.core.files.uploadedfile import SimpleUploadedFile
from modules.conversaciones.domain.models import (
    Conversacion,
    Mensaje,
    MensajeArchivoAdjunto,
    SolicitudConversacion,
)
from modules.tramites.domain.constants import EstadoCambio, EstadoSolicitud
from modules.tramites.domain.models import (
    Expediente,
    Solicitud,
    SolicitudEstadoHistorial,
    SolicitudRespuesta,
    TipoDocumento,
)
from modules.tramites.tests.factories import make_finalizar_solicitud_payload
from modules.usuarios.domain.models import Area, Usuario


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def area(db):
    """A test area."""
    area, _ = Area.objects.get_or_create(
        nombre="Área Test Finalización",
        defaults={
            "descripcion": "Área para tests de finalización",
            "activo": True,
        },
    )
    return area


@pytest.fixture
def cargo_test(db):
    """A test cargo (position/role)."""
    from modules.usuarios.domain.models.cargo import Cargo
    return Cargo.objects.create(
        nombre="Cargo de Prueba Finalización",
        activo=True,
    )


@pytest.fixture
def asignacion_usuario_creador(db, usuario_creador, area, cargo_test):
    """Active area assignment for usuario_creador."""
    from modules.usuarios.domain.models.asignacion_usuario import AsignacionUsuario
    return AsignacionUsuario.objects.create(
        usuario=usuario_creador,
        area=area,
        cargo=cargo_test,
        periodo_inicio=datetime.now(timezone.utc).date(),
        periodo_fin=None,  # Activa
    )


@pytest.fixture
def usuario_creador(db):
    """A test user for the finalizacion flow."""
    user = Usuario.objects.create_user(
        username="operador_finalizacion",
        email="operador@cip.gob.pe",
        password="testpass123",
        dni="12345678",
        nombres="Operador",
        apellidos="Test",
    )
    return user


@pytest.fixture
def tipo_documento(db):
    """A TipoDocumento for the expediente."""
    tipo_doc, _ = TipoDocumento.objects.get_or_create(
        nombre="SOLICITUD",
        defaults={"descripcion": "Tipo documento solicitud"},
    )
    return tipo_doc


@pytest.fixture
def expediente(db, usuario_creador, tipo_documento):
    """A test expediente."""
    return Expediente.objects.create(
        numero=1,
        tipo_persona="NATURAL",
        dni="12345678",
        tipo_documento=tipo_documento,
        numero_documento="DOC-FIN-001",
        numero_folios=5,
        asunto="Trámite para test de finalización",
        fecha_registro=datetime.now(timezone.utc),
        creado_por=usuario_creador,
    )


@pytest.fixture
def solicitud_en_gestion(db, expediente, usuario_creador):
    """A Solicitud in EN_GESTION state."""
    return Solicitud.objects.create(
        expediente=expediente,
        creado_por=usuario_creador,
        estado=EstadoSolicitud.EN_GESTION,
        fecha_registro=datetime.now(timezone.utc),
    )


@pytest.fixture
def solicitud_finalizada(db, expediente, usuario_creador):
    """A Solicitud already FINALIZADA."""
    return Solicitud.objects.create(
        expediente=expediente,
        creado_por=usuario_creador,
        estado=EstadoSolicitud.FINALIZADA,
        fecha_registro=datetime.now(timezone.utc),
        fecha_cierre=datetime.now(timezone.utc),
    )


@pytest.fixture
def solicitud_anulada(db, expediente, usuario_creador):
    """A Solicitud ANULADA."""
    return Solicitud.objects.create(
        expediente=expediente,
        creado_por=usuario_creador,
        estado=EstadoSolicitud.ANULADA,
        fecha_registro=datetime.now(timezone.utc),
    )


@pytest.fixture
def conversacion_vinculada(db, solicitud_en_gestion, usuario_creador):
    """A Conversacion linked to the solicitud via bridge."""
    conv = Conversacion.objects.create(
        titulo=f"Conversación - {solicitud_en_gestion.expediente.id_publico}",
        creada_por=usuario_creador,
        fecha_inicio=datetime.now(timezone.utc),
    )
    SolicitudConversacion.objects.create(
        solicitud=solicitud_en_gestion,
        conversacion=conv,
    )
    return conv


@pytest.fixture
def auth_client(usuario_creador):
    """JWT-authenticated test client."""
    client = TestClient()
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = usuario_creador
    return client


# ── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.django_db(transaction=True)
def test_finalizar_solicitud_content_only_success(
    solicitud_en_gestion,
    conversacion_vinculada,
    usuario_creador,
    asignacion_usuario_creador,
):
    """
    GIVEN:  a valid Solicitud in EN_GESTION with linked conversation
    WHEN:   POST /solicitudes/{id}/finalizar is called with tipo_respuesta + contenido
    THEN:   response status is 200
            AND SolicitudRespuesta is created with es_final=True
            AND Solicitud.estado is FINALIZADA
            AND Solicitud.fecha_cierre is set
            AND SolicitudEstadoHistorial with origen=CIERRE is created
    """
    from config.api import api
    from modules.tramites.domain.models import SolicitudRespuesta

    client = TestClient(api)
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = usuario_creador

    payload = {
        "tipo_respuesta": "INFORME",
        "contenido": "Se emite informe de cierre del trámite.",
        "es_final": "true",
    }

    response = client.post(
        f"/solicitudes/{solicitud_en_gestion.id}/finalizar",
        data={"data": json.dumps(payload)},
        files=[],
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    result = response.json()
    assert result["success"] is True
    data = result["data"]
    assert data["solicitud_estado"] == EstadoSolicitud.FINALIZADA
    assert data["fecha_cierre"] is not None
    assert data["solicitud_respuesta"]["es_final"] is True
    assert data["solicitud_respuesta"]["tipo_respuesta"] == "INFORME"

    # Verify DB state
    respuesta = SolicitudRespuesta.objects.filter(id=data["solicitud_respuesta"]["id"]).first()
    assert respuesta is not None
    assert respuesta.es_final is True
    assert respuesta.tipo_respuesta == "INFORME"

    solicitud_en_gestion.refresh_from_db()
    assert solicitud_en_gestion.estado == EstadoSolicitud.FINALIZADA
    assert solicitud_en_gestion.fecha_cierre is not None

    # Verify historial
    historial = SolicitudEstadoHistorial.objects.filter(
        solicitud=solicitud_en_gestion,
        origen=OrigenCambio.CIERRE,
    ).first()
    assert historial is not None


@pytest.mark.django_db(transaction=True)
def test_finalizar_crea_mensaje_sistema_en_conversacion(
    solicitud_en_gestion,
    conversacion_vinculada,
    usuario_creador,
    asignacion_usuario_creador,
):
    """
    GIVEN:  a valid Solicitud in EN_GESTION with linked conversation
    WHEN:   POST /solicitudes/{id}/finalizar is called
    THEN:   a Mensaje with tipo=SISTEMA is created in the conversacion
            AND SolicitudRespuesta is linked to that mensaje
    """
    from config.api import api

    client = TestClient(api)
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = usuario_creador

    payload = {
        "tipo_respuesta": "CONFORMIDAD",
        "contenido": "Trámite conforme.",
        "es_final": "true",
    }

    response = client.post(
        f"/solicitudes/{solicitud_en_gestion.id}/finalizar",
        data={"data": json.dumps(payload)},
        files=[],
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    result = response.json()["data"]

    # Verify mensaje SISTEMA exists in conversacion
    mensajes_sistema = Mensaje.objects.filter(
        conversacion=conversacion_vinculada,
        tipo="SISTEMA",
    )
    assert mensajes_sistema.count() >= 1

    # Verify SolicitudRespuesta is linked to the mensaje
    respuesta = SolicitudRespuesta.objects.get(id=result["solicitud_respuesta"]["id"])
    assert respuesta.mensaje_id is not None
    assert respuesta.conversacion_id == conversacion_vinculada.id


@pytest.mark.django_db(transaction=True)
def test_finalizar_duplicado_conflicto(
    solicitud_en_gestion,
    conversacion_vinculada,
    usuario_creador,
    area,
):
    """
    GIVEN:  a Solicitud that already has a response with es_final=True
    WHEN:   POST /solicitudes/{id}/finalizar is called again with es_final=True
    THEN:   response status is 409 Conflict
    """
    from config.api import api
    from modules.tramites.domain.models import SolicitudRespuesta

    # First: create the final response
    respuesta_existente = SolicitudRespuesta.objects.create(
        solicitud=solicitud_en_gestion,
        conversacion=conversacion_vinculada,
        mensaje=Mensaje.objects.create(
            conversacion=conversacion_vinculada,
            autor_usuario_id=None,
            contenido="Primera respuesta final",
            tipo="SISTEMA",
            fecha_envio=datetime.now(timezone.utc),
        ),
        area=area,
        tipo_respuesta="INFORME",
        contenido="Primera respuesta final",
        es_final=True,
        emitido_por=usuario_creador,
    )

    client = TestClient(api)
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = usuario_creador

    payload = {
        "tipo_respuesta": "OBSERVACION",
        "contenido": "Intento de segunda respuesta final.",
        "es_final": "true",
    }

    response = client.post(
        f"/solicitudes/{solicitud_en_gestion.id}/finalizar",
        data={"data": json.dumps(payload)},
        files=[],
    )

    assert response.status_code == 409, f"Expected 409, got {response.status_code}"


@pytest.mark.django_db(transaction=True)
def test_finalizar_solicitud_finalizada_conflicto(
    solicitud_finalizada,
    usuario_creador,
):
    """
    GIVEN:  a Solicitud already in FINALIZADA state
    WHEN:   POST /solicitudes/{id}/finalizar is called
    THEN:   response status is 409 Conflict
    """
    from config.api import api

    client = TestClient(api)
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = usuario_creador

    payload = {
        "tipo_respuesta": "INFORME",
        "contenido": "Intento de responder a solicitud ya finalizada.",
        "es_final": "true",
    }

    response = client.post(
        f"/solicitudes/{solicitud_finalizada.id}/finalizar",
        data={"data": json.dumps(payload)},
        files=[],
    )

    assert response.status_code == 409, f"Expected 409, got {response.status_code}"


@pytest.mark.django_db(transaction=True)
def test_finalizar_solicitud_anulada_conflicto(
    solicitud_anulada,
    usuario_creador,
):
    """
    GIVEN:  a Solicitud in ANULADA state
    WHEN:   POST /solicitudes/{id}/finalizar is called
    THEN:   response status is 409 Conflict
    """
    from config.api import api

    client = TestClient(api)
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = usuario_creador

    payload = {
        "tipo_respuesta": "INFORME",
        "contenido": "Intento de responder a solicitud anulada.",
        "es_final": "true",
    }

    response = client.post(
        f"/solicitudes/{solicitud_anulada.id}/finalizar",
        data={"data": json.dumps(payload)},
        files=[],
    )

    assert response.status_code == 409, f"Expected 409, got {response.status_code}"


@pytest.mark.django_db(transaction=True)
def test_finalizar_solicitud_con_archivo_adjunto_exito(
    solicitud_en_gestion,
    conversacion_vinculada,
    usuario_creador,
    asignacion_usuario_creador,
):
    """
    GIVEN:  a valid Solicitud in EN_GESTION with linked conversation
    WHEN:   POST /solicitudes/{id}/finalizar is called with tipo_respuesta,
            contenido, es_final AND one file attachment via multipart FormData
    THEN:   response status is 200
            AND no orphan-file error occurs (parse_form_json correctly hydrates
              the archivo field via token replacement)
            AND SolicitudRespuesta is created with es_final=True
            AND MensajeArchivoAdjunto record is created linked to the mensaje
    """
    from config.api import api
    from django.core.files.uploadedfile import SimpleUploadedFile
    from modules.conversaciones.domain.models import Mensaje, MensajeArchivoAdjunto

    client = TestClient(api)
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = usuario_creador

    # File with token matching the JSON payload
    pdf_content = b"%PDF-1.4 test content for file attachment"
    pdf_file = SimpleUploadedFile(
        name="file_adjunto_token___documento_adjunto.pdf",
        content=pdf_content,
        content_type="application/pdf",
    )

    # JSON payload: archivo field uses the token (without ___realname suffix)
    payload = {
        "tipo_respuesta": "INFORME",
        "contenido": "Informe con archivo adjunto de prueba.",
        "es_final": "true",
        "archivos": [
            {
                "nombre_original": "documento_adjunto.pdf",
                "mime_type": "application/pdf",
                "tamano_bytes": len(pdf_content),
                "archivo": "file_adjunto_token",
            }
        ],
    }

    # Mock FileSystemStorage.save to prevent actual file writes
    with patch(
        "django.core.files.storage.FileSystemStorage.save",
        return_value="conversaciones/archivos/dummy.pdf",
    ):
        response = client.post(
            f"/solicitudes/{solicitud_en_gestion.id}/finalizar",
            data={"data": json.dumps(payload)},
            files=[pdf_file],
        )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.json()}"
    )

    result = response.json()
    assert result["success"] is True
    data = result["data"]
    assert data["solicitud_estado"] == EstadoSolicitud.FINALIZADA
    assert data["solicitud_respuesta"]["es_final"] is True

    # Verify MensajeArchivoAdjunto was created
    respuesta_id = data["solicitud_respuesta"]["id"]
    from modules.tramites.domain.models import SolicitudRespuesta
    respuesta = SolicitudRespuesta.objects.get(id=respuesta_id)
    adjunto_count = MensajeArchivoAdjunto.objects.filter(
        mensaje_id=respuesta.mensaje_id
    ).count()
    assert adjunto_count == 1, (
        f"Expected 1 MensajeArchivoAdjunto, found {adjunto_count}"
    )

    # Verify the adjunto metadata
    adjunto = MensajeArchivoAdjunto.objects.filter(
        mensaje_id=respuesta.mensaje_id
    ).first()
    assert adjunto is not None
    assert adjunto.nombre_original == "documento_adjunto.pdf"
    assert adjunto.mime_type == "application/pdf"


# Alias for use in tests
from modules.tramites.domain.models.solicitud_historial import OrigenCambio


# ── Tests para cierre de períodos ────────────────────────────────────────────────


@pytest.mark.django_db(transaction=True)
def test_finalizar_payload_frontend_sin_es_final_cierra_periodo(
    solicitud_en_gestion,
    conversacion_vinculada,
    usuario_creador,
    asignacion_usuario_creador,
    area,
):
    """The finalizar route must close periods without a client es_final flag."""
    from config.api import api
    from modules.asignaciones.domain.constants import EstadoPeriodo, TipoCierre
    from modules.asignaciones.domain.models import (
        SolicitudAsignacion,
        SolicitudAsignacionPeriodo,
        SolicitudAsignacionPeriodoEstadoHistorial,
    )

    asignacion = SolicitudAsignacion.objects.create(
        solicitud=solicitud_en_gestion,
        area=area,
        fecha_incorporacion=datetime.now(timezone.utc),
        incorporado_por=usuario_creador,
    )
    periodo = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        tipo_participacion=TipoParticipacion.PRINCIPAL,
        estado=EstadoPeriodo.EN_GESTION,
        fecha_inicio=datetime.now(timezone.utc),
        iniciado_por=usuario_creador,
    )

    client = TestClient(api)
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    payload = make_finalizar_solicitud_payload(
        tipo_respuesta="CONFORMIDAD",
        contenido="Trámite conforme, se procede al cierre.",
    )

    response = client.post(
        f"/solicitudes/{solicitud_en_gestion.id}/finalizar",
        data={"data": json.dumps(payload)},
        files=[],
    )

    assert response.status_code == 200, response.json()
    assert response.json()["data"]["solicitud_respuesta"]["es_final"] is True

    solicitud_en_gestion.refresh_from_db()
    periodo.refresh_from_db()
    assert solicitud_en_gestion.estado == EstadoSolicitud.FINALIZADA
    assert solicitud_en_gestion.fecha_cierre is not None
    assert periodo.estado == EstadoPeriodo.CERRADO
    assert periodo.tipo_cierre == TipoCierre.FINALIZADO
    assert periodo.finalizado_por == usuario_creador
    assert SolicitudAsignacionPeriodoEstadoHistorial.objects.filter(
        periodo=periodo,
        origen="FINALIZACION_SOLICITUD",
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_finalizar_cierra_periodos_pendiente_y_en_gestion(
    solicitud_en_gestion,
    conversacion_vinculada,
    usuario_creador,
    asignacion_usuario_creador,
    area,
):
    """
    GIVEN:  a Solicitud in EN_GESTION with two open periods (PENDIENTE and EN_GESTION)
            and one already CERRADO period, each on different assignments/areas
    WHEN:   POST /solicitudes/{id}/finalizar is called with es_final=True
    THEN:   PENDIENTE and EN_GESTION periods are transitioned to CERRADO
            with tipo_cierre=FINALIZADO and motivo_cierre contains 'Cierre de solicitud'
    """
    from config.api import api
    from modules.asignaciones.domain.models import (
        SolicitudAsignacion,
        SolicitudAsignacionPeriodo,
    )
    from modules.asignaciones.domain.constants import TipoParticipacion, TipoCierre
    from modules.usuarios.domain.models import Area

    # Create two more areas for different assignments
    area2 = Area.objects.create(
        nombre="Área Test 2 Finalización",
        descripcion="Segunda área para test",
        activo=True,
    )
    area3 = Area.objects.create(
        nombre="Área Test 3 Finalización",
        descripcion="Tercera área para test",
        activo=True,
    )

    # Create first assignment with PENDIENTE period
    asignacion1 = SolicitudAsignacion.objects.create(
        solicitud=solicitud_en_gestion,
        area=area,
        fecha_incorporacion=datetime.now(timezone.utc),
        incorporado_por=usuario_creador,
    )
    periodo_pendiente = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion1,
        numero_ciclo=1,
        tipo_participacion=TipoParticipacion.PRINCIPAL,
        estado="PENDIENTE",
        fecha_inicio=datetime.now(timezone.utc),
        iniciado_por=usuario_creador,
    )

    # Create second assignment with EN_GESTION period
    asignacion2 = SolicitudAsignacion.objects.create(
        solicitud=solicitud_en_gestion,
        area=area2,
        fecha_incorporacion=datetime.now(timezone.utc),
        incorporado_por=usuario_creador,
    )
    periodo_en_gestion = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion2,
        numero_ciclo=1,
        tipo_participacion=TipoParticipacion.PRINCIPAL,
        estado="EN_GESTION",
        fecha_inicio=datetime.now(timezone.utc),
        iniciado_por=usuario_creador,
    )

    # Create third assignment with CERRADO period
    asignacion3 = SolicitudAsignacion.objects.create(
        solicitud=solicitud_en_gestion,
        area=area3,
        fecha_incorporacion=datetime.now(timezone.utc),
        incorporado_por=usuario_creador,
    )
    periodo_cerrado = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion3,
        numero_ciclo=1,
        tipo_participacion=TipoParticipacion.PRINCIPAL,
        estado="CERRADO",
        fecha_inicio=datetime.now(timezone.utc),
        fecha_fin=datetime.now(timezone.utc),
        iniciado_por=usuario_creador,
        finalizado_por=usuario_creador,
        tipo_cierre=TipoCierre.FINALIZADO,
        motivo_cierre="Cierre previo",
    )

    client = TestClient(api)
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = usuario_creador

    payload = {
        "tipo_respuesta": "CONFORMIDAD",
        "contenido": "Trámite conforme, se procede al cierre.",
        "es_final": "true",
    }

    response = client.post(
        f"/solicitudes/{solicitud_en_gestion.id}/finalizar",
        data={"data": json.dumps(payload)},
        files=[],
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    # Verify PENDIENTE period was closed
    periodo_pendiente.refresh_from_db()
    assert periodo_pendiente.estado == "CERRADO"
    assert periodo_pendiente.tipo_cierre == TipoCierre.FINALIZADO
    assert periodo_pendiente.fecha_fin is not None
    assert periodo_pendiente.finalizado_por == usuario_creador
    assert "Cierre de solicitud" in (periodo_pendiente.motivo_cierre or "")

    # Verify EN_GESTION period was closed
    periodo_en_gestion.refresh_from_db()
    assert periodo_en_gestion.estado == "CERRADO"
    assert periodo_en_gestion.tipo_cierre == TipoCierre.FINALIZADO
    assert periodo_en_gestion.fecha_fin is not None
    assert periodo_en_gestion.finalizado_por == usuario_creador
    assert "Cierre de solicitud" in (periodo_en_gestion.motivo_cierre or "")

    # Verify already CERRADO period was NOT modified
    periodo_cerrado.refresh_from_db()
    assert periodo_cerrado.estado == "CERRADO"
    assert periodo_cerrado.tipo_cierre == TipoCierre.FINALIZADO
    assert periodo_cerrado.motivo_cierre == "Cierre previo"
    assert periodo_cerrado.fecha_fin is not None


@pytest.mark.django_db(transaction=True)
def test_finalizar_crea_historial_periodo_con_finalizacion_solicitud(
    solicitud_en_gestion,
    conversacion_vinculada,
    usuario_creador,
    asignacion_usuario_creador,
    area,
):
    """
    GIVEN:  a Solicitud in EN_GESTION with an open period
    WHEN:   POST /solicitudes/{id}/finalizar is called with es_final=True
    THEN:   SolicitudAsignacionPeriodoEstadoHistorial is created
            with origen=FINALIZACION_SOLICITUD and cambiado_por=usuario_creador
    """
    from config.api import api
    from modules.asignaciones.domain.models import (
        SolicitudAsignacion,
        SolicitudAsignacionPeriodo,
        SolicitudAsignacionPeriodoEstadoHistorial,
    )
    from modules.asignaciones.domain.constants import (
        TipoParticipacion,
        TipoCierre,
        EstadoPeriodoOperativo,
    )
    from modules.usuarios.domain.models import Area

    # Create a second area to avoid unique constraint on open period
    area2 = Area.objects.create(
        nombre="Área Test Historial",
        descripcion="Área para test de historial",
        activo=True,
    )

    asignacion = SolicitudAsignacion.objects.create(
        solicitud=solicitud_en_gestion,
        area=area2,
        fecha_incorporacion=datetime.now(timezone.utc),
        incorporado_por=usuario_creador,
    )
    periodo = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        tipo_participacion=TipoParticipacion.PRINCIPAL,
        estado="EN_GESTION",
        fecha_inicio=datetime.now(timezone.utc),
        iniciado_por=usuario_creador,
    )

    client = TestClient(api)
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = usuario_creador

    payload = {
        "tipo_respuesta": "INFORME",
        "contenido": "Informe de cierre.",
        "es_final": "true",
    }

    response = client.post(
        f"/solicitudes/{solicitud_en_gestion.id}/finalizar",
        data={"data": json.dumps(payload)},
        files=[],
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    # Verify historial was created for the period
    historial = SolicitudAsignacionPeriodoEstadoHistorial.objects.filter(
        periodo=periodo,
        origen="FINALIZACION_SOLICITUD",
    ).first()

    assert historial is not None, "Historial with origen=FINALIZACION_SOLICITUD not found"
    assert historial.cambiado_por == usuario_creador
    assert historial.estado_anterior == EstadoPeriodoOperativo.EN_GESTION
    assert historial.estado_nuevo == EstadoPeriodoOperativo.CERRADO
    assert "Cierre de solicitud" in (historial.motivo or "")


@pytest.mark.django_db(transaction=True)
def test_finalizar_no_crea_historial_adicional_para_periodo_cerrado(
    solicitud_en_gestion,
    conversacion_vinculada,
    usuario_creador,
    asignacion_usuario_creador,
    area,
):
    """
    GIVEN:  a Solicitud in EN_GESTION with an already CERRADO period
    WHEN:   POST /solicitudes/{id}/finalizar is called with es_final=True
    THEN:   no new historial record is created for the already closed period
    """
    from config.api import api
    from modules.asignaciones.domain.models import (
        SolicitudAsignacion,
        SolicitudAsignacionPeriodo,
        SolicitudAsignacionPeriodoEstadoHistorial,
    )
    from modules.asignaciones.domain.constants import TipoParticipacion, TipoCierre
    from modules.usuarios.domain.models import Area

    # Create a second area to avoid unique constraint on open period
    area2 = Area.objects.create(
        nombre="Área Test Cerrado",
        descripcion="Área para test de periodo cerrado",
        activo=True,
    )

    asignacion = SolicitudAsignacion.objects.create(
        solicitud=solicitud_en_gestion,
        area=area2,
        fecha_incorporacion=datetime.now(timezone.utc),
        incorporado_por=usuario_creador,
    )
    periodo_cerrado = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        tipo_participacion=TipoParticipacion.PRINCIPAL,
        estado="CERRADO",
        fecha_inicio=datetime.now(timezone.utc),
        fecha_fin=datetime.now(timezone.utc),
        iniciado_por=usuario_creador,
        finalizado_por=usuario_creador,
        tipo_cierre=TipoCierre.FINALIZADO,
        motivo_cierre="Cierre previo",
    )

    # Count historial records before finalization
    historial_count_before = SolicitudAsignacionPeriodoEstadoHistorial.objects.filter(
        periodo=periodo_cerrado
    ).count()

    client = TestClient(api)
    token = AccessToken.for_user(usuario_creador)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = usuario_creador

    payload = {
        "tipo_respuesta": "CONFORMIDAD",
        "contenido": "Se cierra la solicitud.",
        "es_final": "true",
    }

    response = client.post(
        f"/solicitudes/{solicitud_en_gestion.id}/finalizar",
        data={"data": json.dumps(payload)},
        files=[],
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"

    # Verify no new historial was created for the already closed period
    historial_count_after = SolicitudAsignacionPeriodoEstadoHistorial.objects.filter(
        periodo=periodo_cerrado
    ).count()

    assert historial_count_after == historial_count_before, (
        f"Expected no new historial for already closed period, but got {historial_count_after - historial_count_before} new records"
    )
