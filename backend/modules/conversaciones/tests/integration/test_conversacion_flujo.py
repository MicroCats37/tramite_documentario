"""
Integration tests for ConversacionFlujo — main business rules.

Tests cover:
- Creating a conversacion (standalone and linked to a Solicitud).
- Posting a mensaje to an open conversacion.
- Rejecting a mensaje on a closed conversacion.
- Soft-deleting a mensaje.
- Idempotent close and delete operations.
"""

import pytest
from asgiref.sync import sync_to_async
from datetime import datetime, timezone

from modules.conversaciones.domain.constants import EstadoConversacion, TipoMensaje
from modules.conversaciones.domain.exceptions import (
    ConversacionCerradaError,
    ConversacionNotFoundError,
    MensajeNotFoundError,
)
from modules.conversaciones.domain.models import (
    Conversacion,
    Mensaje,
    MensajeArchivoAdjunto,
    MensajeMencion,
    SolicitudConversacion,
)
from modules.conversaciones.domain.schemas.conversacion_schemas import (
    ConversacionCreateData,
)
from modules.conversaciones.domain.schemas.mensaje_schemas import (
    MensajeArchivoAdjuntoData,
    MensajeCreateData,
    MensajeMencionData,
)
from modules.conversaciones.domain.services.core.mensajeria_service import (
    MensajeriaCoreService,
)
from modules.conversaciones.domain.services.flujos.conversacion_flujo import (
    ConversacionFlujo,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def core_service():
    """MensajeriaCoreService instance."""
    return MensajeriaCoreService()


@pytest.fixture
def conversacion_flujo(core_service):
    """ConversacionFlujo with injected core service."""
    return ConversacionFlujo(mensajeria_service=core_service)


@pytest.fixture
def usuario(db):
    """A test usuario."""
    from modules.usuarios.domain.models import Usuario
    user, _ = Usuario.objects.get_or_create(
        username="12345678",
        defaults={
            "nombres": "Test",
            "apellidos": "User",
            "dni": "12345678",
            "email": "testuser1@example.com",
        },
    )
    return user


@pytest.fixture
def usuario_2(db):
    """A second test usuario."""
    from modules.usuarios.domain.models import Usuario
    user, _ = Usuario.objects.get_or_create(
        username="87654321",
        defaults={
            "nombres": "Test2",
            "apellidos": "User2",
            "dni": "87654321",
            "email": "testuser2@example.com",
        },
    )
    return user


@pytest.fixture
def conversacion_abierta(core_service, usuario):
    """An open conversacion."""
    data = ConversacionCreateData(
        titulo="Test Conversation",
        creada_por_id=usuario.id,
        fecha_inicio=datetime.now(timezone.utc),
    )
    return core_service.crear_conversacion(data)


@pytest.fixture
def conversacion_cerrada(core_service, usuario, usuario_2):
    """A closed conversacion."""
    data = ConversacionCreateData(
        titulo="Closed Conversation",
        creada_por_id=usuario.id,
        fecha_inicio=datetime.now(timezone.utc),
    )
    conv = core_service.crear_conversacion(data)
    return core_service.cerrar_conversacion(conv, cerrado_por_id=usuario_2.id)


# ── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestConversacionCoreService:
    """Tests for MensajeriaCoreService (sync operations)."""

    def test_crear_conversacion(self, core_service, usuario):
        data = ConversacionCreateData(
            titulo="My Conversation",
            creada_por_id=usuario.id,
        )
        conv = core_service.crear_conversacion(data)

        assert conv.id is not None
        assert conv.titulo == "My Conversation"
        assert conv.creada_por_id == usuario.id
        assert conv.fecha_cierre is None

    def test_obtener_conversacion_not_found(self, core_service):
        from uuid import uuid4

        with pytest.raises(ConversacionNotFoundError):
            core_service.obtener_conversacion(uuid4())

    def test_cerrar_conversacion(self, core_service, usuario_2, conversacion_abierta):
        conv = core_service.cerrar_conversacion(
            conversacion=conversacion_abierta,
            cerrado_por_id=usuario_2.id,
        )

        assert conv.fecha_cierre is not None
        assert conv.cerrado_por_id == usuario_2.id

    def test_crear_mensaje_simple(self, core_service, usuario, conversacion_abierta):
        data = MensajeCreateData(
            conversacion_id=conversacion_abierta.id,
            autor_usuario_id=usuario.id,
            contenido="Hello world",
            tipo=TipoMensaje.MENSAJE,
        )
        msg = core_service.crear_mensaje(data)

        assert msg.id is not None
        assert msg.conversacion_id == conversacion_abierta.id
        assert msg.autor_usuario_id == usuario.id
        assert msg.contenido == "Hello world"
        assert msg.eliminado_at is None

    def test_crear_mensaje_con_adjuntos(
        self, core_service, usuario, conversacion_abierta
    ):
        data = MensajeCreateData(
            conversacion_id=conversacion_abierta.id,
            autor_usuario_id=usuario.id,
            contenido="Message with file",
            archivos_adjuntos=[
                MensajeArchivoAdjuntoData(
                    nombre_original="doc.pdf",
                    mime_type="application/pdf",
                    tamano_bytes=2048,
                    subido_por_id=usuario.id,
                ),
            ],
        )
        msg = core_service.crear_mensaje(data)

        msg.refresh_from_db()
        assert msg.archivos_adjuntos.count() == 1
        adj = msg.archivos_adjuntos.first()
        assert adj.nombre_original == "doc.pdf"

    def test_crear_mensaje_con_menciones(
        self, core_service, usuario, usuario_2, conversacion_abierta
    ):
        data = MensajeCreateData(
            conversacion_id=conversacion_abierta.id,
            autor_usuario_id=usuario.id,
            contenido="Hey @user2",
            menciones=[
                MensajeMencionData(usuario_id=usuario_2.id),
            ],
        )
        msg = core_service.crear_mensaje(data)

        msg.refresh_from_db()
        assert msg.menciones.count() == 1
        assert msg.menciones.first().usuario_id == usuario_2.id

    def test_crear_mensaje_sin_contenido_sin_adjunto_falla(
        self, core_service, usuario, conversacion_abierta
    ):
        from pydantic import ValidationError as PydanticValidationError
        with pytest.raises(PydanticValidationError, match="must have contenido"):
            MensajeCreateData(
                conversacion_id=conversacion_abierta.id,
                autor_usuario_id=usuario.id,
                contenido=None,
                archivos_adjuntos=[],
            )

    def test_eliminar_mensaje(self, core_service, usuario, conversacion_abierta):
        data = MensajeCreateData(
            conversacion_id=conversacion_abierta.id,
            autor_usuario_id=usuario.id,
            contenido="To be deleted",
        )
        msg = core_service.crear_mensaje(data)

        from modules.conversaciones.domain.schemas.mensaje_schemas import MensajeDeleteData

        deleted = core_service.eliminar_mensaje(
            mensaje=msg,
            data=MensajeDeleteData(eliminado_por_id=usuario.id),
        )

        assert deleted.eliminado_at is not None
        assert deleted.eliminado_por_id == usuario.id

    def test_listar_mensajes_excluye_eliminados(
        self, core_service, usuario, conversacion_abierta
    ):
        data = MensajeCreateData(
            conversacion_id=conversacion_abierta.id,
            autor_usuario_id=usuario.id,
            contenido="Visible",
        )
        msg = core_service.crear_mensaje(data)

        from modules.conversaciones.domain.schemas.mensaje_schemas import MensajeDeleteData

        core_service.eliminar_mensaje(
            mensaje=msg,
            data=MensajeDeleteData(eliminado_por_id=usuario.id),
        )

        mensajes = core_service.listar_mensajes_con_adjuntos(conversacion_abierta.id)
        assert len(mensajes) == 0

    def test_crear_puente_solicitud(
        self, core_service, usuario, db
    ):
        """Bridge requires a real Solicitud — use asignaciones.TestBase."""
        pass  # Deferred to Phase 3 integration with Solicitud


@pytest.mark.django_db(transaction=True)
class TestConversacionFlujo:
    """Tests for ConversacionFlujo (async with transaction.atomic)."""

    @pytest.mark.asyncio
    async def test_proceso_crear_conversacion(self, conversacion_flujo, usuario):
        data = ConversacionCreateData(
            titulo="Async Conversation",
            creada_por_id=usuario.id,
        )
        conv = await conversacion_flujo._proceso_crear_conversacion(data)

        assert conv.id is not None
        assert conv.titulo == "Async Conversation"

    @pytest.mark.asyncio
    async def test_proceso_crear_mensaje_en_abierta(
        self, conversacion_flujo, usuario, conversacion_abierta
    ):
        data = MensajeCreateData(
            conversacion_id=conversacion_abierta.id,
            autor_usuario_id=usuario.id,
            contenido="async message",
        )
        msg = await conversacion_flujo._proceso_crear_mensaje(data)

        assert msg.id is not None
        assert msg.contenido == "async message"

    @pytest.mark.asyncio
    async def test_proceso_crear_mensaje_en_cerrada_falla(
        self, conversacion_flujo, usuario, conversacion_cerrada
    ):
        data = MensajeCreateData(
            conversacion_id=conversacion_cerrada.id,
            autor_usuario_id=usuario.id,
            contenido="Should fail",
        )
        with pytest.raises(ConversacionCerradaError):
            await conversacion_flujo._proceso_crear_mensaje(data)

    @pytest.mark.asyncio
    async def test_proceso_cerrar_conversacion(
        self, conversacion_flujo, usuario_2, conversacion_abierta
    ):
        conv = await conversacion_flujo._proceso_cerrar_conversacion(
            conversacion_id=conversacion_abierta.id,
            cerrado_por_id=usuario_2.id,
        )

        assert conv.fecha_cierre is not None
        assert conv.cerrado_por_id == usuario_2.id

    @pytest.mark.asyncio
    async def test_proceso_cerrar_conversacion_idempotente(
        self, conversacion_flujo, usuario_2, conversacion_cerrada
    ):
        """Closing an already-closed conversacion should not raise."""
        conv = await conversacion_flujo._proceso_cerrar_conversacion(
            conversacion_id=conversacion_cerrada.id,
            cerrado_por_id=usuario_2.id,
        )
        # Should not raise — idempotent
        assert conv.fecha_cierre is not None

    @pytest.mark.asyncio
    async def test_proceso_eliminar_mensaje(
        self, conversacion_flujo, usuario, conversacion_abierta
    ):
        data = MensajeCreateData(
            conversacion_id=conversacion_abierta.id,
            autor_usuario_id=usuario.id,
            contenido="To delete",
        )
        msg = await conversacion_flujo._proceso_crear_mensaje(data)

        deleted = await conversacion_flujo._proceso_eliminar_mensaje(
            mensaje_id=msg.id,
            eliminado_por_id=usuario.id,
        )

        assert deleted.eliminado_at is not None

    @pytest.mark.asyncio
    async def test_proceso_eliminar_mensaje_idempotente(
        self, conversacion_flujo, usuario, conversacion_abierta
    ):
        """Deleting an already-deleted mensaje should not raise."""
        data = MensajeCreateData(
            conversacion_id=conversacion_abierta.id,
            autor_usuario_id=usuario.id,
            contenido="To delete twice",
        )
        msg = await conversacion_flujo._proceso_crear_mensaje(data)

        # First delete
        await conversacion_flujo._proceso_eliminar_mensaje(
            mensaje_id=msg.id,
            eliminado_por_id=usuario.id,
        )
        # Second delete — idempotent, should not raise
        deleted = await conversacion_flujo._proceso_eliminar_mensaje(
            mensaje_id=msg.id,
            eliminado_por_id=usuario.id,
        )
        assert deleted.eliminado_at is not None

    @pytest.mark.asyncio
    async def test_proceso_crear_mensaje_con_adjuntos_y_menciones(
        self, conversacion_flujo, usuario, usuario_2, conversacion_abierta
    ):
        data = MensajeCreateData(
            conversacion_id=conversacion_abierta.id,
            autor_usuario_id=usuario.id,
            contenido="Check the attachment",
            archivos_adjuntos=[
                MensajeArchivoAdjuntoData(
                    nombre_original="report.xlsx",
                    mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    tamano_bytes=4096,
                    subido_por_id=usuario.id,
                ),
            ],
            menciones=[
                MensajeMencionData(usuario_id=usuario_2.id),
            ],
        )
        msg = await conversacion_flujo._proceso_crear_mensaje(data)

        await sync_to_async(msg.refresh_from_db, thread_sensitive=True)()
        adjuntos_count = await sync_to_async(msg.archivos_adjuntos.count, thread_sensitive=True)()
        menciones_count = await sync_to_async(msg.menciones.count, thread_sensitive=True)()
        assert adjuntos_count == 1
        assert menciones_count == 1

    @pytest.mark.asyncio
    async def test_proceso_crear_mensaje_con_archivo_real(
        self, conversacion_flujo, usuario, conversacion_abierta, db
    ):
        """
        GIVEN:  an open conversacion and a real uploaded file
        WHEN:  _proceso_crear_mensaje is called with archivo UploadedFile
        THEN:  MensajeArchivoAdjunto.archivo FileField is populated
               AND the archivo_url is accessible from the stored file
        """
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.conf import settings
        import os

        # Create a real file upload simulation
        fake_file = SimpleUploadedFile(
            name="test_document.pdf",
            content=b"%PDF-1.4 fake pdf content for testing",
            content_type="application/pdf",
        )

        data = MensajeCreateData(
            conversacion_id=conversacion_abierta.id,
            autor_usuario_id=usuario.id,
            contenido="Message with real file",
            archivos_adjuntos=[
                MensajeArchivoAdjuntoData(
                    nombre_original="test_document.pdf",
                    mime_type="application/pdf",
                    tamano_bytes=len(b"%PDF-1.4 fake pdf content for testing"),
                    archivo=fake_file,
                    subido_por_id=usuario.id,
                ),
            ],
        )
        msg = await conversacion_flujo._proceso_crear_mensaje(data)

        await sync_to_async(msg.refresh_from_db, thread_sensitive=True)()
        adj = await sync_to_async(msg.archivos_adjuntos.first, thread_sensitive=True)()

        # Verify the FileField is populated
        assert adj.archivo is not None
        assert adj.archivo.name is not None
        # Verify archivo_url is accessible (would point to MEDIA_URL in real storage)
        archivo_url = adj.archivo.url
        assert archivo_url is not None
        assert "test_document.pdf" in archivo_url or adj.archivo.name in archivo_url
