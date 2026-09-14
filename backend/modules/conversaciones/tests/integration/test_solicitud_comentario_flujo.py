"""
Integration tests for SolicitudComentarioFlujo — contextual comment operations.

Tests cover:
- Creating a comment on a bridge-validated conversation.
- Bridge validation: mismatched solicitud/conversacion returns error.
- Normal comment (no mentions) creates no notification.
- Comment with mentions creates NotificacionUsuario and NotificacionSolicitud
  with conversacion and mensaje context.
"""

import pytest
from asgiref.sync import sync_to_async
from datetime import datetime, timezone

from modules.conversaciones.domain.constants import TipoMensaje
from modules.conversaciones.domain.exceptions import BridgeValidationError
from modules.conversaciones.domain.models import (
    Conversacion,
    Mensaje,
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
from modules.conversaciones.domain.services.flujos.solicitud_comentario_flujo import (
    SolicitudComentarioFlujo,
)
from modules.notificaciones.domain.models import Notificacion, NotificacionSolicitud


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def core_service():
    """MensajeriaCoreService instance."""
    return MensajeriaCoreService()


@pytest.fixture
def solicitud_comentario_flujo(core_service):
    """SolicitudComentarioFlujo with injected core service."""
    return SolicitudComentarioFlujo(mensajeria_service=core_service)


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
def area(db):
    """A test area."""
    from modules.usuarios.domain.models import Area
    area, _ = Area.objects.get_or_create(
        nombre="Área Test Comentarios",
        defaults={
            "descripcion": "Área para tests de comentarios",
            "activo": True,
        },
    )
    return area


@pytest.fixture
def solicitud(db, area, usuario):
    """A test solicitud linked to the area."""
    from datetime import datetime, timezone
    from modules.tramites.domain.models import Solicitud, Expediente, TipoDocumento
    from modules.tramites.domain.constants import EstadoSolicitud

    tipo_doc, _ = TipoDocumento.objects.get_or_create(
        nombre="SOLICITUD",
        defaults={"descripcion": "Tipo documento solicitud"},
    )
    expediente = Expediente.objects.create(
        numero=1,
        tipo_persona="NATURAL",
        dni="12345678",
        tipo_documento=tipo_doc,
        numero_documento="DOC-SOL-001",
        numero_folios=5,
        asunto="Trámite de prueba",
        fecha_registro=datetime.now(timezone.utc),
        creado_por=usuario,
    )
    solicitud = Solicitud.objects.create(
        expediente=expediente,
        creado_por=usuario,
        estado=EstadoSolicitud.EN_GESTION,
        fecha_registro=datetime.now(timezone.utc),
    )
    return solicitud


@pytest.fixture
def conversacion_abierta(core_service, usuario):
    """An open conversacion (not linked to solicitud)."""
    data = ConversacionCreateData(
        titulo="Test Conversation",
        creada_por_id=usuario.id,
        fecha_inicio=datetime.now(timezone.utc),
    )
    return core_service.crear_conversacion(data)


@pytest.fixture
def conversacion_linked(core_service, usuario, solicitud):
    """A conversacion linked to the solicitud via bridge."""
    data = ConversacionCreateData(
        titulo="Linked Conversation",
        creada_por_id=usuario.id,
        fecha_inicio=datetime.now(timezone.utc),
    )
    conv = core_service.crear_conversacion(data)
    core_service.crear_puente_solicitud(
        solicitud_id=solicitud.id,
        conversacion=conv,
    )
    return conv


# ── Tests ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
class TestSolicitudComentarioFlujo:
    """Tests for SolicitudComentarioFlujo (async with transaction.atomic)."""

    @pytest.mark.asyncio
    async def test_crear_comentario_normal_crea_mensaje_sin_notificacion(
        self,
        solicitud_comentario_flujo,
        usuario,
        conversacion_linked,
        solicitud,
    ):
        """
        GIVEN:  a valid bridge-linked conversacion and usuario
        WHEN:   _proceso_crear_comentario is called WITHOUT mentions
        THEN:   Mensaje is created
                AND no Notificacion is created
        """
        data = MensajeCreateData(
            conversacion_id=conversacion_linked.id,
            autor_usuario_id=usuario.id,
            contenido="Comentario normal sin menciones",
        )
        msg = await solicitud_comentario_flujo._proceso_crear_comentario(
            data=data,
            solicitud_id=solicitud.id,
        )

        assert msg.id is not None
        assert msg.contenido == "Comentario normal sin menciones"
        assert msg.conversacion_id == conversacion_linked.id

        # Verify no notification was created
        notificacion_count = await sync_to_async(
            Notificacion.objects.filter(
                evento="COMENTARIO_MENCION"
            ).count,
            thread_sensitive=True,
        )()
        assert notificacion_count == 0

    @pytest.mark.asyncio
    async def test_crear_comentario_con_menciones_crea_notificacion(
        self,
        solicitud_comentario_flujo,
        usuario,
        usuario_2,
        conversacion_linked,
        solicitud,
    ):
        """
        GIVEN:  a valid bridge-linked conversacion and two usuarios
        WHEN:   _proceso_crear_comentario is called WITH a mention of usuario_2
        THEN:   Mensaje is created
                AND MensajeMencion is created for usuario_2
                AND Notificacion (COMENTARIO_MENCION) is created
                AND NotificacionUsuario is created for usuario_2
                AND NotificacionSolicitud is created with conversacion and mensaje
        """
        data = MensajeCreateData(
            conversacion_id=conversacion_linked.id,
            autor_usuario_id=usuario.id,
            contenido="Hola @usuario2",
            menciones=[
                MensajeMencionData(usuario_id=usuario_2.id),
            ],
        )
        msg = await solicitud_comentario_flujo._proceso_crear_comentario(
            data=data,
            solicitud_id=solicitud.id,
        )

        assert msg.id is not None
        assert msg.contenido == "Hola @usuario2"

        # Verify mention was created
        await sync_to_async(msg.refresh_from_db, thread_sensitive=True)()
        menciones_count = await sync_to_async(msg.menciones.count, thread_sensitive=True)()
        assert menciones_count == 1

        # Verify notification was created
        notificacion_count = await sync_to_async(
            lambda: Notificacion.objects.filter(
                evento="COMENTARIO_MENCION"
            ).count(),
            thread_sensitive=True,
        )()
        assert notificacion_count == 1

        # Verify NotificacionUsuario exists for usuario_2
        notificacion = await sync_to_async(
            lambda: Notificacion.objects.get(evento="COMENTARIO_MENCION"),
            thread_sensitive=True,
        )()
        notificacion_usuario_count = await sync_to_async(
            lambda: notificacion.usuarios_notificados.count(),
            thread_sensitive=True,
        )()
        assert notificacion_usuario_count == 1

        # Verify NotificacionSolicitud has conversacion and mensaje
        notificacion_solicitud = await sync_to_async(
            lambda: NotificacionSolicitud.objects.get(notificacion=notificacion),
            thread_sensitive=True,
        )()
        assert notificacion_solicitud.conversacion_id == conversacion_linked.id
        assert notificacion_solicitud.mensaje_id == msg.id
        assert notificacion_solicitud.solicitud_id == solicitud.id

    @pytest.mark.asyncio
    async def test_crear_comentario_mismatched_bridge_raises_error(
        self,
        solicitud_comentario_flujo,
        usuario,
        conversacion_abierta,  # NOT linked to any solicitud
        solicitud,
    ):
        """
        GIVEN:  a conversacion that is NOT linked to any solicitud
        WHEN:   _proceso_crear_comentario is called with that conversacion
        THEN:   BridgeValidationError is raised
        """
        data = MensajeCreateData(
            conversacion_id=conversacion_abierta.id,
            autor_usuario_id=usuario.id,
            contenido="Este comentario debería fallar",
        )
        with pytest.raises(BridgeValidationError):
            await solicitud_comentario_flujo._proceso_crear_comentario(
                data=data,
                solicitud_id=solicitud.id,
            )

    @pytest.mark.asyncio
    async def test_crear_comentario_wrong_solicitud_raises_error(
        self,
        solicitud_comentario_flujo,
        usuario,
        conversacion_linked,
        db,
    ):
        """
        GIVEN:  a conversacion linked to one solicitud
        WHEN:   _proceso_crear_comentario is called with a DIFFERENT solicitud_id
        THEN:   BridgeValidationError is raised
        """
        from modules.tramites.domain.models import Solicitud
        from modules.tramites.domain.constants import EstadoSolicitud
        from modules.usuarios.domain.models import Area

        # Create a different area and solicitud
        other_area, _ = await sync_to_async(Area.objects.get_or_create, thread_sensitive=True)(
            nombre="ÁreaOtra",
            defaults={
                "descripcion": "Otra área",
                "activo": True,
            },
        )
        from datetime import datetime, timezone
        from modules.tramites.domain.models import Expediente, TipoDocumento
        tipo_doc, _ = await sync_to_async(TipoDocumento.objects.get_or_create, thread_sensitive=True)(
            nombre="SOLICITUD",
            defaults={"descripcion": "Tipo documento solicitud"},
        )
        other_expediente = await sync_to_async(Expediente.objects.create, thread_sensitive=True)(
            numero=9999,
            tipo_persona="NATURAL",
            dni="87654321",
            tipo_documento=tipo_doc,
            numero_documento="DOC-SOL-9999",
            numero_folios=3,
            asunto="Otro trámite de prueba",
            fecha_registro=datetime.now(timezone.utc),
            creado_por=usuario,
        )
        other_solicitud = await sync_to_async(Solicitud.objects.create, thread_sensitive=True)(
            expediente=other_expediente,
            creado_por=usuario,
            estado=EstadoSolicitud.EN_GESTION,
            fecha_registro=datetime.now(timezone.utc),
        )

        data = MensajeCreateData(
            conversacion_id=conversacion_linked.id,
            autor_usuario_id=usuario.id,
            contenido="Este comentario debería fallar",
        )
        with pytest.raises(BridgeValidationError):
            await solicitud_comentario_flujo._proceso_crear_comentario(
                data=data,
                solicitud_id=other_solicitud.id,
            )

    @pytest.mark.asyncio
    async def test_crear_comentario_conversation_cerrada_raises_error(
        self,
        solicitud_comentario_flujo,
        usuario,
        conversacion_linked,
        solicitud,
    ):
        """
        GIVEN:  a closed conversacion linked to a solicitud
        WHEN:   _proceso_crear_comentario is called
        THEN:   ConversacionCerradaError is raised
        """
        from modules.conversaciones.domain.exceptions import ConversacionCerradaError

        # Close the conversation
        await sync_to_async(
            conversacion_linked.__class__.objects.filter(
                id=conversacion_linked.id
            ).update,
            thread_sensitive=True,
        )(fecha_cierre=datetime.now(timezone.utc), cerrado_por_id=usuario.id)

        data = MensajeCreateData(
            conversacion_id=conversacion_linked.id,
            autor_usuario_id=usuario.id,
            contenido="No debería funcionar",
        )
        with pytest.raises(ConversacionCerradaError):
            await solicitud_comentario_flujo._proceso_crear_comentario(
                data=data,
                solicitud_id=solicitud.id,
            )

    @pytest.mark.asyncio
    async def test_crear_comentario_multiple_menciones_crea_multiples_notificaciones(
        self,
        solicitud_comentario_flujo,
        usuario,
        usuario_2,
        conversacion_linked,
        solicitud,
        db,
    ):
        """
        GIVEN:  a valid bridge-linked conversacion and three usuarios
        WHEN:   _proceso_crear_comentario is called with mentions of usuario_2 and a third user
        THEN:   Two Notificacion records are created (one per mentioned user)
                AND two NotificacionUsuario records are created (one per mentioned user)
                AND two NotificacionSolicitud records are created (one per notification)
        """
        from modules.usuarios.domain.models import Usuario

        # Create a third user
        usuario_3, _ = await sync_to_async(Usuario.objects.get_or_create, thread_sensitive=True)(
            username="11223344",
            defaults={
                "nombres": "Test3",
                "apellidos": "User3",
                "dni": "11223344",
                "email": "testuser3@example.com",
            },
        )

        data = MensajeCreateData(
            conversacion_id=conversacion_linked.id,
            autor_usuario_id=usuario.id,
            contenido="Hola a ambos @usuario2 y @usuario3",
            menciones=[
                MensajeMencionData(usuario_id=usuario_2.id),
                MensajeMencionData(usuario_id=usuario_3.id),
            ],
        )
        msg = await solicitud_comentario_flujo._proceso_crear_comentario(
            data=data,
            solicitud_id=solicitud.id,
        )

        assert msg.id is not None

        # Verify two mentions
        await sync_to_async(msg.refresh_from_db, thread_sensitive=True)()
        menciones_count = await sync_to_async(msg.menciones.count, thread_sensitive=True)()
        assert menciones_count == 2

        # Verify two notifications (one per mentioned user)
        notificacion_count = await sync_to_async(
            lambda: Notificacion.objects.filter(
                evento="COMENTARIO_MENCION",
                contexto_solicitud__mensaje=msg,
            ).count(),
            thread_sensitive=True,
        )()
        assert notificacion_count == 2

        # Each notification should have exactly 1 user (the mentioned one)
        for notif in await sync_to_async(
            lambda: list(Notificacion.objects.filter(
                evento="COMENTARIO_MENCION",
                contexto_solicitud__mensaje=msg,
            )),
            thread_sensitive=True,
        )():
            user_count = await sync_to_async(
                lambda: notif.usuarios_notificados.count(),
                thread_sensitive=True,
            )()
            assert user_count == 1


# ── System Message Tests ────────────────────────────────────────────────────────


@pytest.mark.django_db(transaction=True)
class TestSolicitudComentarioFlujoSystemMessages:
    """Tests for system message creation in SolicitudComentarioFlujo."""

    @pytest.mark.asyncio
    async def test_crear_mensaje_sistema_con_autor_nulo(
        self,
        solicitud_comentario_flujo,
        usuario,
        conversacion_linked,
        solicitud,
    ):
        """
        GIVEN:  a valid bridge-linked conversacion
        WHEN:   _proceso_crear_mensaje_sistema is called with autor_usuario=None
        THEN:   Mensaje is created with tipo=SISTEMA and autor_usuario=None
        """
        msg = await solicitud_comentario_flujo._proceso_crear_mensaje_sistema(
            conversacion_id=conversacion_linked.id,
            contenido="Mensaje del sistema",
            solicitud_id=solicitud.id,
        )

        assert msg.id is not None
        assert msg.tipo == TipoMensaje.SISTEMA
        assert msg.autor_usuario_id is None
        assert msg.contenido == "Mensaje del sistema"

    @pytest.mark.asyncio
    async def test_mensaje_sistema_no_crea_notificacion(
        self,
        solicitud_comentario_flujo,
        usuario,
        conversacion_linked,
        solicitud,
    ):
        """
        GIVEN:  a valid bridge-linked conversacion
        WHEN:   _proceso_crear_mensaje_sistema is called
        THEN:   Mensaje is created
                AND no Notificacion is created
        """
        msg = await solicitud_comentario_flujo._proceso_crear_mensaje_sistema(
            conversacion_id=conversacion_linked.id,
            contenido="Mensaje del sistema sin notificacion",
            solicitud_id=solicitud.id,
        )

        assert msg.id is not None

        # Verify no notification was created
        notificacion_count = await sync_to_async(
            Notificacion.objects.all().count,
            thread_sensitive=True,
        )()
        assert notificacion_count == 0

    @pytest.mark.asyncio
    async def test_mensaje_sistema_en_conversacion_cerrada_falla(
        self,
        solicitud_comentario_flujo,
        usuario,
        conversacion_linked,
        solicitud,
    ):
        """
        GIVEN:  a closed conversacion linked to a solicitud
        WHEN:   _proceso_crear_mensaje_sistema is called
        THEN:   ConversacionCerradaError is raised
        """
        from modules.conversaciones.domain.exceptions import ConversacionCerradaError

        # Close the conversation
        await sync_to_async(
            conversacion_linked.__class__.objects.filter(
                id=conversacion_linked.id
            ).update,
            thread_sensitive=True,
        )(fecha_cierre=datetime.now(timezone.utc), cerrado_por_id=usuario.id)

        with pytest.raises(ConversacionCerradaError):
            await solicitud_comentario_flujo._proceso_crear_mensaje_sistema(
                conversacion_id=conversacion_linked.id,
                contenido="No debería funcionar",
                solicitud_id=solicitud.id,
            )

    @pytest.mark.asyncio
    async def test_mensaje_sistema_mismatched_bridge_raises_error(
        self,
        solicitud_comentario_flujo,
        conversacion_abierta,  # NOT linked to any solicitud
        solicitud,
    ):
        """
        GIVEN:  a conversacion that is NOT linked to any solicitud
        WHEN:   _proceso_crear_mensaje_sistema is called with that conversacion
        THEN:   BridgeValidationError is raised
        """
        with pytest.raises(BridgeValidationError):
            await solicitud_comentario_flujo._proceso_crear_mensaje_sistema(
                conversacion_id=conversacion_abierta.id,
                contenido="Este mensaje debería fallar",
                solicitud_id=solicitud.id,
            )


@pytest.mark.django_db
class TestMensajeCreateDataValidators:
    """Tests for MensajeCreateData schema validators."""

    def test_humano_sin_autor_falla(self, usuario, conversacion_abierta):
        """
        GIVEN:  a valid conversacion
        WHEN:   MensajeCreateData is created with tipo!=SISTEMA and autor_usuario_id=None
        THEN:   ValidationError is raised
        """
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError, match="Non-system messages must have autor_usuario_id"):
            MensajeCreateData(
                conversacion_id=conversacion_abierta.id,
                autor_usuario_id=None,
                contenido="Mensaje sin autor",
                tipo="MENSAJE",
            )

    def test_sistema_con_autor_falla(self, usuario, conversacion_abierta):
        """
        GIVEN:  a valid conversacion
        WHEN:   MensajeCreateData is created with tipo=SISTEMA and autor_usuario_id set
        THEN:   ValidationError is raised
        """
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError, match="System messages must have autor_usuario_id=null"):
            MensajeCreateData(
                conversacion_id=conversacion_abierta.id,
                autor_usuario_id=usuario.id,
                contenido="Mensaje sistema con autor",
                tipo="SISTEMA",
            )

    def test_sistema_sin_autor_pasa(self, conversacion_abierta):
        """
        GIVEN:  a valid conversacion
        WHEN:   MensajeCreateData is created with tipo=SISTEMA and autor_usuario_id=None
        THEN:   No validation error is raised
        """
        data = MensajeCreateData(
            conversacion_id=conversacion_abierta.id,
            autor_usuario_id=None,
            contenido="Mensaje del sistema",
            tipo="SISTEMA",
        )
        assert data.tipo == "SISTEMA"
        assert data.autor_usuario_id is None

    def test_humano_con_autor_pasa(self, usuario, conversacion_abierta):
        """
        GIVEN:  a valid conversacion and usuario
        WHEN:   MensajeCreateData is created with tipo=MENSAJE and autor_usuario_id set
        THEN:   No validation error is raised
        """
        data = MensajeCreateData(
            conversacion_id=conversacion_abierta.id,
            autor_usuario_id=usuario.id,
            contenido="Mensaje normal",
            tipo="MENSAJE",
        )
        assert data.tipo == "MENSAJE"
        assert data.autor_usuario_id == usuario.id

