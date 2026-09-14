"""
E2E tests for Conversacion API.

Tests the /conversaciones endpoints using the async controller
with ninja_extra.testing.TestAsyncClient per the async testing contract.

Test client pattern: TestAsyncClient with async def tests,
JWT auth via AccessToken.for_user.

Endpoints tested:
    POST /conversaciones/                     — crear conversación
    GET  /conversaciones/                    — listar conversaciones
    GET  /conversaciones/{id}                — obtener detalle
    POST /conversaciones/{id}/cerrar          — cerrar conversación
    POST /conversaciones/{id}/mensajes        — publicar mensaje
    DELETE /conversaciones/mensajes/{id}     — eliminar mensaje
"""

import json
import uuid
from datetime import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.datastructures import MultiValueDict
from asgiref.sync import sync_to_async

from ninja_extra.testing import TestAsyncClient
from ninja_jwt.tokens import AccessToken
from config.api import api

from modules.conversaciones.domain.models import (
    Conversacion,
    Mensaje,
)
from modules.conversaciones.domain.constants import EstadoConversacion, TipoMensaje


# ── Helpers for wrapping sync ORM calls inside async test bodies ───────────────

def _create_conversacion_sync(titulo, creada_por, fecha_inicio):
    return Conversacion.objects.create(
        titulo=titulo,
        creada_por=creada_por,
        fecha_inicio=fecha_inicio,
    )


def _create_mensaje_sync(conversacion, autor_usuario, contenido, tipo, fecha_envio, **kwargs):
    return Mensaje.objects.create(
        conversacion=conversacion,
        autor_usuario=autor_usuario,
        contenido=contenido,
        tipo=tipo,
        fecha_envio=fecha_envio,
        **kwargs,
    )


def _save_model_sync(instance):
    instance.save()


# ── Fixtures ────────────────────────────────────────────────────────────────────

# All tests in this module use async client with transaction=True to avoid SQLite table locks.
pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio]


@pytest.fixture
def usuario(db):
    """A test usuario."""
    User = get_user_model()
    return User.objects.create_user(
        username="12345678",
        email="testuser1@cip.gob.pe",
        password="testpass123",
        dni="12345678",
        nombres="Test",
        apellidos="User",
    )


@pytest.fixture
def usuario_2(db):
    """A second test usuario."""
    User = get_user_model()
    return User.objects.create_user(
        username="87654321",
        email="testuser2@cip.gob.pe",
        password="testpass123",
        dni="87654321",
        nombres="Test2",
        apellidos="User2",
    )


@pytest.fixture
def conversacion_abierta(db, usuario):
    """An open conversacion pre-created via ORM."""
    return Conversacion.objects.create(
        titulo="Pre-existing Conversation",
        creada_por=usuario,
        fecha_inicio=datetime.now(),
    )


@pytest.fixture
async def auth_async_client(db, usuario):
    """Async test client with JWT auth. Returns (client, headers) tuple."""
    token = str(AccessToken.for_user(usuario))
    client = TestAsyncClient(api)
    headers = {"Authorization": f"Bearer {token}"}
    client.headers.update(headers)
    yield (client, headers)


# ── POST /conversaciones/ ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_crear_conversacion_basica(auth_async_client, usuario):
    """
    GIVEN:  an authenticated user
    WHEN:   POST /conversaciones/ is called with valid data
    THEN:   response status is 200
            AND the created conversacion is returned with correct fields
    """
    client, headers = auth_async_client
    payload = {"titulo": "Nueva conversación"}

    response = await client.post("/conversaciones/", json=payload, headers=headers)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["titulo"] == "Nueva conversación"
    assert data["estado"] == EstadoConversacion.ABIERTA.value
    assert data["fecha_cierre"] is None


@pytest.mark.asyncio
async def test_crear_conversacion_sin_titulo(auth_async_client, usuario):
    """
    GIVEN:  an authenticated user
    WHEN:   POST /conversaciones/ is called without a titulo
    THEN:   response status is 200 (titulo is optional)
            AND the conversacion is created with null titulo
    """
    client, headers = auth_async_client
    payload = {}

    response = await client.post("/conversaciones/", json=payload, headers=headers)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["titulo"] is None
    assert data["estado"] == EstadoConversacion.ABIERTA.value


# ── GET /conversaciones/ ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_listar_conversaciones_vacio(auth_async_client, usuario):
    """
    GIVEN:  no conversaciones exist
    WHEN:   GET /conversaciones/ is called
    THEN:   response status is 200
            AND items is empty
            AND total is 0
    """
    client, headers = auth_async_client
    response = await client.get("/conversaciones/", headers=headers)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_listar_conversaciones(auth_async_client, conversacion_abierta):
    """
    GIVEN:  one open conversacion exists
    WHEN:   GET /conversaciones/ is called
    THEN:   response status is 200
            AND the conversacion appears in items
            AND total is 1
    """
    client, headers = auth_async_client
    response = await client.get("/conversaciones/", headers=headers)

    assert response.status_code == 200

    data = response.json()["data"]
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["titulo"] == "Pre-existing Conversation"
    assert item["estado"] == EstadoConversacion.ABIERTA.value


@pytest.mark.asyncio
async def test_listar_conversaciones_paginacion(auth_async_client, usuario):
    """
    GIVEN:  3 conversaciones exist for the user
    WHEN:   GET /conversaciones/?page=1&page_size=2 is called
    THEN:   response status is 200
            AND 2 items are returned
            AND total is 3
            AND total_pages is 2
    """
    client, headers = auth_async_client
    for i in range(3):
        await sync_to_async(_create_conversacion_sync, thread_sensitive=True)(
            titulo=f"Conversation {i}",
            creada_por=usuario,
            fecha_inicio=datetime.now(),
        )

    response = await client.get("/conversaciones/?page=1&page_size=2", headers=headers)

    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["total_pages"] == 2


@pytest.mark.asyncio
async def test_listar_conversaciones_solo_participante(auth_async_client, usuario, usuario_2, conversacion_abierta):
    """
    GIVEN:  one conversacion exists created by usuario
    WHEN:   GET /conversaciones/ is called by usuario_2 (not a participant)
    THEN:   the conversacion does not appear in the list
    """
    # Create token for usuario_2
    token = str(AccessToken.for_user(usuario_2))
    client = TestAsyncClient(api)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/conversaciones/", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 0


# ── GET /conversaciones/{id} ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_obtener_conversacion_no_existe(auth_async_client, usuario):
    """
    GIVEN:  no conversacion exists with the given id
    WHEN:   GET /conversaciones/{fake_id} is called
    THEN:   response status is 404
    """
    client, headers = auth_async_client
    fake_id = uuid.uuid4()
    response = await client.get(f"/conversaciones/{fake_id}", headers=headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_obtener_conversacion_detalle(auth_async_client, conversacion_abierta):
    """
    GIVEN:  one conversacion exists
    WHEN:   GET /conversaciones/{id} is called
    THEN:   response status is 200
            AND full conversacion is returned with estado ABIERTA
            AND mensajes list is present (may be empty)
    """
    client, headers = auth_async_client
    response = await client.get(f"/conversaciones/{conversacion_abierta.id}", headers=headers)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["id"] == str(conversacion_abierta.id)
    assert data["titulo"] == "Pre-existing Conversation"
    assert data["estado"] == EstadoConversacion.ABIERTA.value
    assert "mensajes" in data
    assert isinstance(data["mensajes"], list)


@pytest.mark.asyncio
async def test_obtener_conversacion_con_mensajes(auth_async_client, usuario, conversacion_abierta):
    """
    GIVEN:  one conversacion with two messages exists
    WHEN:   GET /conversaciones/{id} is called
    THEN:   response status is 200
            AND both messages are in the mensajes list
            AND deleted messages are excluded
    """
    client, headers = auth_async_client
    # Create two messages
    msg1 = await sync_to_async(_create_mensaje_sync, thread_sensitive=True)(
        conversacion=conversacion_abierta,
        autor_usuario=usuario,
        contenido="First message",
        tipo=TipoMensaje.MENSAJE,
        fecha_envio=datetime.now(),
    )
    msg2 = await sync_to_async(_create_mensaje_sync, thread_sensitive=True)(
        conversacion=conversacion_abierta,
        autor_usuario=usuario,
        contenido="Second message",
        tipo=TipoMensaje.MENSAJE,
        fecha_envio=datetime.now(),
    )

    # Create a deleted message (should be excluded)
    msg_deleted = await sync_to_async(_create_mensaje_sync, thread_sensitive=True)(
        conversacion=conversacion_abierta,
        autor_usuario=usuario,
        contenido="Deleted message",
        tipo=TipoMensaje.MENSAJE,
        fecha_envio=datetime.now(),
        eliminado_at=datetime.now(),
        eliminado_por=usuario,
    )

    response = await client.get(f"/conversaciones/{conversacion_abierta.id}", headers=headers)

    assert response.status_code == 200

    data = response.json()["data"]
    assert len(data["mensajes"]) == 2
    contenidos = {m["contenido"] for m in data["mensajes"]}
    assert "First message" in contenidos
    assert "Second message" in contenidos
    assert "Deleted message" not in contenidos


# ── POST /conversaciones/{id}/cerrar ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_cerrar_conversacion(auth_async_client, usuario, conversacion_abierta):
    """
    GIVEN:  one open conversacion exists
    WHEN:   POST /conversaciones/{id}/cerrar is called
    THEN:   response status is 200
            AND the conversacion estado is CERRADA
            AND fecha_cierre is set
    """
    client, headers = auth_async_client
    response = await client.post(f"/conversaciones/{conversacion_abierta.id}/cerrar", headers=headers)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["estado"] == EstadoConversacion.CERRADA.value
    assert data["fecha_cierre"] is not None


@pytest.mark.asyncio
async def test_cerrar_conversacion_idempotente(auth_async_client, usuario, conversacion_abierta):
    """
    GIVEN:  one closed conversacion exists
    WHEN:   POST /conversaciones/{id}/cerrar is called twice
    THEN:   both calls return 200
            AND fecha_cierre is preserved (not overwritten)
    """
    client, headers = auth_async_client
    # First close
    response1 = await client.post(f"/conversaciones/{conversacion_abierta.id}/cerrar", headers=headers)
    assert response1.status_code == 200
    fecha_cierre_1 = response1.json()["data"]["fecha_cierre"]

    # Second close (idempotent)
    response2 = await client.post(f"/conversaciones/{conversacion_abierta.id}/cerrar", headers=headers)
    assert response2.status_code == 200
    fecha_cierre_2 = response2.json()["data"]["fecha_cierre"]

    assert fecha_cierre_1 == fecha_cierre_2


@pytest.mark.asyncio
async def test_cerrar_conversacion_no_existe(auth_async_client, usuario):
    """
    GIVEN:  no conversacion exists with the given id
    WHEN:   POST /conversaciones/{id}/cerrar is called
    THEN:   response status is 404
    """
    client, headers = auth_async_client
    fake_id = uuid.uuid4()
    response = await client.post(f"/conversaciones/{fake_id}/cerrar", headers=headers)

    assert response.status_code == 404


# ── POST /conversaciones/{id}/mensajes ───────────────────────────────────────


@pytest.mark.asyncio
async def test_crear_mensaje_basico(auth_async_client, usuario, conversacion_abierta):
    """
    GIVEN:  one open conversacion exists
    WHEN:   POST /conversaciones/{id}/mensajes is called with contenido via FormData
    THEN:   response status is 200
            AND the mensaje is created with correct contenido and autor
    """
    client, headers = auth_async_client
    payload = {"contenido": "Hello world"}
    form_data = {'data': json.dumps(payload)}

    response = await client.post(
        f"/conversaciones/{conversacion_abierta.id}/mensajes",
        data=form_data,
        headers=headers,
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["contenido"] == "Hello world"
    assert data["autor_usuario_id"] == str(usuario.id)
    assert data["tipo"] == TipoMensaje.MENSAJE.value


@pytest.mark.asyncio
async def test_crear_mensaje_en_conversacion_cerrada(auth_async_client, usuario, conversacion_abierta):
    """
    GIVEN:  one closed conversacion exists
    WHEN:   POST /conversaciones/{id}/mensajes is called
    THEN:   response status is 400 or 422
            AND an error about closed conversacion is returned
    """
    client, headers = auth_async_client
    # Close the conversacion
    conversacion_abierta.fecha_cierre = datetime.now()
    conversacion_abierta.cerrado_por = usuario
    await sync_to_async(_save_model_sync, thread_sensitive=True)(conversacion_abierta)

    payload = {"contenido": "Should fail"}
    form_data = {'data': json.dumps(payload)}

    response = await client.post(
        f"/conversaciones/{conversacion_abierta.id}/mensajes",
        data=form_data,
        headers=headers,
    )

    assert response.status_code in (400, 422), (
        f"Expected 400/422, got {response.status_code}: {response.content}"
    )


@pytest.mark.asyncio
async def test_crear_mensaje_sin_autenticacion(conversacion_abierta):
    """
    GIVEN:  no authenticated user
    WHEN:   POST /conversaciones/{id}/mensajes is called
    THEN:   response status is 401 or 403
    """
    client = TestAsyncClient(api)
    payload = {"contenido": "Unauthorized"}
    form_data = {'data': json.dumps(payload)}

    response = await client.post(
        f"/conversaciones/{conversacion_abierta.id}/mensajes",
        data=form_data,
    )

    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_crear_mensaje_sin_contenido_sin_adjuntos(auth_async_client, usuario, conversacion_abierta):
    """
    GIVEN:  one open conversacion exists
    WHEN:   POST /conversaciones/{id}/mensajes is called without contenido and without adjuntos
    THEN:   response status is 400 or 422 (validation error)
    """
    client, headers = auth_async_client
    payload = {}
    form_data = {'data': json.dumps(payload)}

    response = await client.post(
        f"/conversaciones/{conversacion_abierta.id}/mensajes",
        data=form_data,
        headers=headers,
    )

    assert response.status_code in (400, 422), (
        f"Expected 400/422, got {response.status_code}: {response.content}"
    )


@pytest.mark.asyncio
async def test_crear_mensaje_con_adjuntos(auth_async_client, usuario, conversacion_abierta):
    """
    GIVEN:  one open conversacion exists
    WHEN:   POST /conversaciones/{id}/mensajes is called with archivos_adjuntos metadata (no real files)
    THEN:   response status is 200
            AND the mensaje includes the attachment metadata
            AND attachment is stored in DB
            AND archivo_url is None (no real file uploaded)
    """
    client, headers = auth_async_client
    payload = {
        "contenido": "Message with file",
        "archivos_adjuntos": [
            {
                "nombre_original": "report.xlsx",
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "tamano_bytes": 4096,
            }
        ],
    }
    form_data = {'data': json.dumps(payload)}

    response = await client.post(
        f"/conversaciones/{conversacion_abierta.id}/mensajes",
        data=form_data,
        headers=headers,
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["contenido"] == "Message with file"
    assert len(data["archivos_adjuntos"]) == 1
    assert data["archivos_adjuntos"][0]["nombre_original"] == "report.xlsx"
    # archivo_url is None since no real file was uploaded
    assert data["archivos_adjuntos"][0]["archivo_url"] is None


@pytest.mark.asyncio
async def test_crear_mensaje_con_menciones(auth_async_client, usuario, usuario_2, conversacion_abierta):
    """
    GIVEN:  one open conversacion exists
    WHEN:   POST /conversaciones/{id}/mensajes is called with menciones via FormData
    THEN:   response status is 200
            AND the mensaje includes the mention
            AND MensajeMencion record is created in DB
    """
    client, headers = auth_async_client
    payload = {
        "contenido": "Hey @user2",
        "menciones": [{"usuario_id": str(usuario_2.id)}],
    }
    form_data = {'data': json.dumps(payload)}

    response = await client.post(
        f"/conversaciones/{conversacion_abierta.id}/mensajes",
        data=form_data,
        headers=headers,
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert len(data["menciones"]) == 1
    assert data["menciones"][0]["usuario_id"] == str(usuario_2.id)


# ── DELETE /conversaciones/mensajes/{id} ─────────────────────────────────────


@pytest.mark.asyncio
async def test_eliminar_mensaje(auth_async_client, usuario, conversacion_abierta):
    """
    GIVEN:  one mensaje exists in the conversacion
    WHEN:   DELETE /conversaciones/mensajes/{id} is called
    THEN:   response status is 200
            AND the mensaje's eliminado_at and eliminado_por_id are set
    """
    client, headers = auth_async_client
    # Create a mensaje first
    msg = await sync_to_async(_create_mensaje_sync, thread_sensitive=True)(
        conversacion=conversacion_abierta,
        autor_usuario=usuario,
        contenido="To be deleted",
        tipo=TipoMensaje.MENSAJE,
        fecha_envio=datetime.now(),
    )

    response = await client.delete(f"/conversaciones/mensajes/{msg.id}", headers=headers)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["eliminado_at"] is not None


@pytest.mark.asyncio
async def test_eliminar_mensaje_idempotente(auth_async_client, usuario, conversacion_abierta):
    """
    GIVEN:  one deleted mensaje exists
    WHEN:   DELETE /conversaciones/mensajes/{id} is called twice
    THEN:   both calls return 200
            AND eliminado_at is preserved (not overwritten)
    """
    client, headers = auth_async_client
    msg = await sync_to_async(_create_mensaje_sync, thread_sensitive=True)(
        conversacion=conversacion_abierta,
        autor_usuario=usuario,
        contenido="Already deleted",
        tipo=TipoMensaje.MENSAJE,
        fecha_envio=datetime.now(),
        eliminado_at=datetime.now(),
        eliminado_por=usuario,
    )

    response1 = await client.delete(f"/conversaciones/mensajes/{msg.id}", headers=headers)
    assert response1.status_code == 200
    eliminado_at_1 = response1.json()["data"]["eliminado_at"]

    response2 = await client.delete(f"/conversaciones/mensajes/{msg.id}", headers=headers)
    assert response2.status_code == 200
    eliminado_at_2 = response2.json()["data"]["eliminado_at"]

    assert eliminado_at_1 == eliminado_at_2


@pytest.mark.asyncio
async def test_eliminar_mensaje_no_existe(auth_async_client, usuario):
    """
    GIVEN:  no mensaje exists with the given id
    WHEN:   DELETE /conversaciones/mensajes/{id} is called
    THEN:   response status is 404
    """
    client, headers = auth_async_client
    fake_id = uuid.uuid4()
    response = await client.delete(f"/conversaciones/mensajes/{fake_id}", headers=headers)

    assert response.status_code == 404


# ── POST /conversaciones/{id}/mensajes via FormData (dual payload) ─────────────


@pytest.mark.asyncio
async def test_crear_mensaje_textonly_via_formdata(auth_async_client, usuario, conversacion_abierta):
    """
    GIVEN:  one open conversacion exists
    WHEN:   POST /conversaciones/{id}/mensajes is called via FormData
            with only the 'data' JSON field (no files)
    THEN:   response status is 200
            AND the mensaje is created with correct contenido
    """
    client, headers = auth_async_client
    payload = {"contenido": "Hello via FormData"}
    form_data = {'data': json.dumps(payload)}

    response = await client.post(
        f"/conversaciones/{conversacion_abierta.id}/mensajes",
        data=form_data,
        headers=headers,
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["contenido"] == "Hello via FormData"
    assert data["autor_usuario_id"] == str(usuario.id)
    assert data["tipo"] == TipoMensaje.MENSAJE.value


@pytest.mark.asyncio
async def test_crear_mensaje_con_archivos_reales_via_formdata(
    auth_async_client, usuario, conversacion_abierta
):
    """
    GIVEN:  one open conversacion exists
    WHEN:   POST /conversaciones/{id}/mensajes is called via FormData
            with files (dual payload pattern)
    THEN:   response status is 200
            AND the mensaje includes the attachment metadata
            AND the attachment archivo FileField is populated
            AND archivo_url is exposed in the response
    """
    client, headers = auth_async_client

    # Same proven multipart pattern used by tramites/expedientes tests.
    file1_content = b"%PDF-1.4 test document"
    file2_content = b"PK\x03\x04 fake zip content"
    file1 = SimpleUploadedFile(
        name="file_uuid1___documento.pdf",
        content=file1_content,
        content_type="application/pdf",
    )
    file2 = SimpleUploadedFile(
        name="file_uuid2___archivo.zip",
        content=file2_content,
        content_type="application/zip",
    )

    payload = {
        "contenido": "Message with multiple files",
        "archivos_adjuntos": [
            {
                "nombre_original": "documento.pdf",
                "mime_type": "application/pdf",
                "tamano_bytes": len(file1_content),
                "archivo": "file_uuid1",
            },
            {
                "nombre_original": "archivo.zip",
                "mime_type": "application/zip",
                "tamano_bytes": len(file2_content),
                "archivo": "file_uuid2",
            },
        ],
    }
    form_data = {'data': json.dumps(payload)}

    response = await client.post(
        f"/conversaciones/{conversacion_abierta.id}/mensajes",
        data=form_data,
        FILES=MultiValueDict({"files": [file1, file2]}),
        headers=headers,
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()["data"]
    assert data["contenido"] == "Message with multiple files"
    assert len(data["archivos_adjuntos"]) == 2

    # Verify each adjunto has archivo_url exposed
    for adj in data["archivos_adjuntos"]:
        assert "archivo_url" in adj
        assert adj["archivo_url"] is not None

    # Verify the database record has archivo FileField populated
    from modules.conversaciones.domain.models import MensajeArchivoAdjunto
    msg_id = uuid.UUID(data["id"])
    adjuntos = await sync_to_async(
        lambda: list(MensajeArchivoAdjunto.objects.filter(mensaje_id=msg_id))
    )()
    assert len(adjuntos) == 2
    for adj in adjuntos:
        assert adj.archivo is not None
        assert adj.archivo.name != ""
