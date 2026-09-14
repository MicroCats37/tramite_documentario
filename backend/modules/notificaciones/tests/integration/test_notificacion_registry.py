"""
Tests for the notification event registry.

Tests:
- Registry entries exist for all registered (ambito, evento) pairs
- get_event_config returns correct EventConfig for registered events
- is_registered_event returns True for registered events
- is_registered_event returns False for unregistered events
- All EventoNotificacion values are registered
- crear_notificacion_area raises ValueError for unregistered events
- crear_notificacion_usuario raises ValueError for unregistered events
- Existing crear_notificacion_area calls with registered events still work
- Existing crear_notificacion_usuario calls with registered events still work
"""

import pytest

from modules.notificaciones.domain.constants import (
    AmbitoNotificacion,
    CategoriaNotificacion,
    EventoNotificacion,
    PrioridadNotificacion,
)
from modules.notificaciones.domain.registry import (
    AmbitoAudience,
    EventConfig,
    NOTIFICACION_REGISTRY,
    get_event_config,
    is_registered_event,
)


# ── Registry structure tests ─────────────────────────────────────────────────────


class TestRegistryCompleteness:
    """Every defined EventoNotificacion value must be registered."""

    @pytest.mark.parametrize(
        "ambito,evento",
        [
            (AmbitoNotificacion.SOLICITUD, EventoNotificacion.ASIGNACION_CREADA),
            (AmbitoNotificacion.SOLICITUD, EventoNotificacion.DEVOLUCION_CREADA),
            (AmbitoNotificacion.SOLICITUD, EventoNotificacion.RESPUESTA_CREADA),
            (AmbitoNotificacion.SOLICITUD, EventoNotificacion.COMENTARIO_MENCION),
            (AmbitoNotificacion.SOLICITUD, EventoNotificacion.COMENTARIO_CREADO),
            (AmbitoNotificacion.SOLICITUD, EventoNotificacion.RECORDATORIO),
        ],
    )
    def test_solicitud_eventos_registered(self, ambito, evento):
        """All SOLICITUD events must be registered."""
        assert is_registered_event(ambito, evento), (
            f"Evento ({ambito}, {evento}) should be registered"
        )

    def test_sistema_recordatorio_registered(self):
        """SISTEMA/RECORDATORIO event must be registered."""
        assert is_registered_event(
            AmbitoNotificacion.SISTEMA, EventoNotificacion.RECORDATORIO
        )

    def test_all_evento_values_registered(self):
        """Every EventoNotificacion value must appear in the registry."""
        for evento in EventoNotificacion.values():
            if evento == EventoNotificacion.RECORDATORIO:
                # RECORDATORIO appears under both SOLICITUD and SISTEMA
                assert is_registered_event(
                    AmbitoNotificacion.SOLICITUD, evento
                ) or is_registered_event(AmbitoNotificacion.SISTEMA, evento), (
                    f"Evento {evento} must be registered under at least one ámbito"
                )
            else:
                assert is_registered_event(AmbitoNotificacion.SOLICITUD, evento), (
                    f"Evento {evento} must be registered"
                )


class TestRegistryLookup:
    """get_event_config returns correct config for registered events."""

    def test_asignacion_creada_config(self):
        """ASIGNACION_CREADA must have correct config."""
        config = get_event_config(
            AmbitoNotificacion.SOLICITUD, EventoNotificacion.ASIGNACION_CREADA
        )
        assert config is not None
        assert config.categoria == CategoriaNotificacion.INSTITUCIONAL
        assert config.default_audiencia == AmbitoAudience.AREA
        assert config.wrapper_type == "solicitud"
        assert config.navigation_target == "solicitud"
        assert config.prioridad_default == PrioridadNotificacion.NORMAL

    def test_comentario_mencion_config(self):
        """COMENTARIO_MENCION must have correct config."""
        config = get_event_config(
            AmbitoNotificacion.SOLICITUD, EventoNotificacion.COMENTARIO_MENCION
        )
        assert config is not None
        assert config.categoria == CategoriaNotificacion.MENSAJERIA
        assert config.default_audiencia == AmbitoAudience.USUARIO
        assert config.wrapper_type == "solicitud_comentario"
        assert config.navigation_target == "comentario"
        assert config.prioridad_default == PrioridadNotificacion.NORMAL

    def test_devolucion_creada_config(self):
        """DEVOLUCION_CREADA must have correct config."""
        config = get_event_config(
            AmbitoNotificacion.SOLICITUD, EventoNotificacion.DEVOLUCION_CREADA
        )
        assert config is not None
        assert config.categoria == CategoriaNotificacion.INSTITUCIONAL
        assert config.default_audiencia == AmbitoAudience.AREA
        assert config.wrapper_type == "solicitud"
        assert config.navigation_target == "solicitud"
        assert config.prioridad_default == PrioridadNotificacion.ALTA

    def test_respuesta_creada_config(self):
        """RESPUESTA_CREADA must have correct config."""
        config = get_event_config(
            AmbitoNotificacion.SOLICITUD, EventoNotificacion.RESPUESTA_CREADA
        )
        assert config is not None
        assert config.categoria == CategoriaNotificacion.INSTITUCIONAL
        assert config.default_audiencia == AmbitoAudience.AREA
        assert config.wrapper_type == "solicitud"
        assert config.navigation_target == "solicitud"
        assert config.prioridad_default == PrioridadNotificacion.ALTA

    def test_comentario_creado_config(self):
        """COMENTARIO_CREADO (legacy) must have correct config."""
        config = get_event_config(
            AmbitoNotificacion.SOLICITUD, EventoNotificacion.COMENTARIO_CREADO
        )
        assert config is not None
        assert config.categoria == CategoriaNotificacion.MENSAJERIA
        assert config.default_audiencia == AmbitoAudience.USUARIO
        assert config.wrapper_type == "solicitud_comentario"
        assert config.navigation_target == "comentario"

    def test_recordatorio_config(self):
        """RECORDATORIO under SOLICITUD must have correct config."""
        config = get_event_config(
            AmbitoNotificacion.SOLICITUD, EventoNotificacion.RECORDATORIO
        )
        assert config is not None
        assert config.categoria == CategoriaNotificacion.SISTEMA
        assert config.default_audiencia == AmbitoAudience.AREA
        assert config.wrapper_type == "solicitud"
        assert config.navigation_target == "solicitud"

    def test_sistema_recordatorio_config(self):
        """SISTEMA/RECORDATORIO must have correct config."""
        config = get_event_config(
            AmbitoNotificacion.SISTEMA, EventoNotificacion.RECORDATORIO
        )
        assert config is not None
        assert config.categoria == CategoriaNotificacion.SISTEMA
        assert config.default_audiencia == AmbitoAudience.AREA
        assert config.wrapper_type == "sistema"
        assert config.navigation_target == "sistema"

    def test_unknown_event_returns_none(self):
        """Unknown (ambito, evento) returns None."""
        config = get_event_config("SOLICITUD", "EVENTO_DESCONOCIDO")
        assert config is None

    def test_unknown_ambito_returns_none(self):
        """Unknown ámbito returns None."""
        config = get_event_config("AMBITO_FALSO", EventoNotificacion.ASIGNACION_CREADA)
        assert config is None


class TestRegistryValidation:
    """is_registered_event correctly identifies registered and unregistered events."""

    @pytest.mark.parametrize("evento", EventoNotificacion.values())
    def test_all_evento_notificacion_values_are_registered_under_solicitud(
        self, evento
    ):
        """All EventoNotificacion values return True for SOLICITUD ámbito."""
        if evento == EventoNotificacion.RECORDATORIO:
            # RECORDATORIO is under both SOLICITUD and SISTEMA
            assert is_registered_event(AmbitoNotificacion.SOLICITUD, evento)
        else:
            assert is_registered_event(AmbitoNotificacion.SOLICITUD, evento)

    def test_unknown_event_returns_false(self):
        """Unknown evento returns False."""
        assert (
            is_registered_event(
                AmbitoNotificacion.SOLICITUD, "EVENTO_FALSO"
            )
            is False
        )

    def test_unknown_ambito_returns_false(self):
        """Unknown ámbito returns False."""
        assert (
            is_registered_event("AMBITO_FALSO", EventoNotificacion.ASIGNACION_CREADA)
            is False
        )

    def test_empty_event_string_returns_false(self):
        """Empty evento string returns False."""
        assert is_registered_event(AmbitoNotificacion.SOLICITUD, "") is False


class TestEventConfigDataclass:
    """EventConfig is a proper frozen dataclass."""

    def test_event_config_is_frozen(self):
        """EventConfig must be immutable."""
        config = get_event_config(
            AmbitoNotificacion.SOLICITUD, EventoNotificacion.ASIGNACION_CREADA
        )
        with pytest.raises(AttributeError):
            config.categoria = "nuevo_valor"

    def test_event_config_has_slots(self):
        """EventConfig uses __slots__ for memory efficiency."""
        config = get_event_config(
            AmbitoNotificacion.SOLICITUD, EventoNotificacion.ASIGNACION_CREADA
        )
        assert hasattr(type(config), "__slots__")

    def test_event_config_fields(self):
        """EventConfig has all required fields."""
        config = get_event_config(
            AmbitoNotificacion.SOLICITUD, EventoNotificacion.ASIGNACION_CREADA
        )
        assert hasattr(config, "categoria")
        assert hasattr(config, "default_audiencia")
        assert hasattr(config, "wrapper_type")
        assert hasattr(config, "navigation_target")
        assert hasattr(config, "prioridad_default")


# ── Service integration: registry validation ────────────────────────────────────


@pytest.fixture
def service():
    from modules.notificaciones.domain.services.core.notificacion_service import (
        NotificacionService,
    )
    return NotificacionService()


@pytest.fixture
def area_test(db):
    from modules.usuarios.domain.models import Area
    return Area.objects.create(
        nombre="Área Test Registry",
        descripcion="Área para tests de registry",
        activo=True,
    )


@pytest.fixture
def usuario_test(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="test_registry_user",
        email="test_registry@cip.gob.pe",
        password="testpass123",
        dni="99999999",
        nombres="Test",
        apellidos="Registry",
    )


@pytest.fixture
def asignacion_usuario_activa(db, usuario_test, area_test):
    from datetime import date
    from modules.usuarios.domain.models import AsignacionUsuario, Cargo
    cargo = Cargo.objects.create(nombre="Cargo Test", activo=True)
    return AsignacionUsuario.objects.create(
        usuario=usuario_test,
        area=area_test,
        cargo=cargo,
        periodo_inicio=date.today(),
        periodo_fin=None,
    )


@pytest.mark.django_db
def test_crear_notificacion_area_rejects_unknown_event(
    service, area_test, usuario_test, asignacion_usuario_activa
):
    """
    GIVEN:  an unknown (ambito, evento) pair
    WHEN:   crear_notificacion_area is called with the unknown pair
    THEN:   NotificacionEventoNoRegistradoError is raised with a descriptive message
    """
    from datetime import datetime
    from modules.notificaciones.domain.exceptions import (
        NotificacionEventoNoRegistradoError,
    )

    with pytest.raises(NotificacionEventoNoRegistradoError) as exc_info:
        service.crear_notificacion_area(
            area=area_test,
            titulo="Test",
            mensaje="Test mensaje",
            ambito="SOLICITUD",
            evento="EVENTO_DESCONOCIDO",
            prioridad=PrioridadNotificacion.NORMAL,
            generada_por_id=usuario_test.id,
            ocurrido_en=datetime.now(),
        )
    assert exc_info.value.ambito == "SOLICITUD"
    assert exc_info.value.evento == "EVENTO_DESCONOCIDO"
    assert "no registrado" in str(exc_info.value)


@pytest.mark.django_db
def test_crear_notificacion_usuario_rejects_unknown_event(
    service, usuario_test
):
    """
    GIVEN:  an unknown (ambito, evento) pair
    WHEN:   crear_notificacion_usuario is called with the unknown pair
    THEN:   NotificacionEventoNoRegistradoError is raised with a descriptive message
    """
    from datetime import datetime
    from modules.notificaciones.domain.exceptions import (
        NotificacionEventoNoRegistradoError,
    )

    with pytest.raises(NotificacionEventoNoRegistradoError) as exc_info:
        service.crear_notificacion_usuario(
            usuario_id=usuario_test.id,
            titulo="Test",
            mensaje="Test mensaje",
            ambito="SOLICITUD",
            evento="EVENTO_FALSO",
            prioridad=PrioridadNotificacion.NORMAL,
            generada_por_id=usuario_test.id,
            ocurrido_en=datetime.now(),
        )
    assert exc_info.value.ambito == "SOLICITUD"
    assert exc_info.value.evento == "EVENTO_FALSO"
    assert "no registrado" in str(exc_info.value)


@pytest.mark.django_db
def test_crear_notificacion_area_accepts_registered_events(
    service, area_test, usuario_test, asignacion_usuario_activa
):
    """
    GIVEN:  a valid area with active user assignment
    WHEN:   crear_notificacion_area is called with each registered SOLICITUD event
    THEN:   no exception is raised and a Notificacion is created
    """
    from datetime import datetime

    for evento in EventoNotificacion.values():
        # Skip SISTEMA events (tested separately)
        notificacion = service.crear_notificacion_area(
            area=area_test,
            titulo=f"Notificación {evento}",
            mensaje="Test mensaje",
            ambito=AmbitoNotificacion.SOLICITUD,
            evento=evento,
            prioridad=PrioridadNotificacion.NORMAL,
            generada_por_id=usuario_test.id,
            ocurrido_en=datetime.now(),
        )
        assert notificacion is not None
        assert notificacion.ambito == AmbitoNotificacion.SOLICITUD
        assert notificacion.evento == evento


@pytest.mark.django_db
def test_crear_notificacion_usuario_accepts_registered_events(service, usuario_test):
    """
    GIVEN:  a valid usuario
    WHEN:   crear_notificacion_usuario is called with each registered SOLICITUD event
    THEN:   no exception is raised and a Notificacion is created
    """
    from datetime import datetime

    for evento in EventoNotificacion.values():
        # Skip SISTEMA events (tested separately)
        notificacion = service.crear_notificacion_usuario(
            usuario_id=usuario_test.id,
            titulo=f"Notificación {evento}",
            mensaje="Test mensaje",
            ambito=AmbitoNotificacion.SOLICITUD,
            evento=evento,
            prioridad=PrioridadNotificacion.NORMAL,
            generada_por_id=usuario_test.id,
            ocurrido_en=datetime.now(),
        )
        assert notificacion is not None
        assert notificacion.ambito == AmbitoNotificacion.SOLICITUD
        assert notificacion.evento == evento


@pytest.mark.django_db
def test_registry_service_integration_full_flow(
    service, area_test, usuario_test, asignacion_usuario_activa
):
    """
    GIVEN:  a registered event ASIGNACION_CREADA
    WHEN:   crear_notificacion_area is called
    THEN:   notification is created AND registry lookup yields correct config
    """
    from datetime import datetime
    from modules.notificaciones.domain.models import Notificacion

    notificacion = service.crear_notificacion_area(
        area=area_test,
        titulo="Nueva asignación creada",
        mensaje="Se ha creado una nueva asignación",
        ambito=AmbitoNotificacion.SOLICITUD,
        evento=EventoNotificacion.ASIGNACION_CREADA,
        prioridad=PrioridadNotificacion.NORMAL,
        generada_por_id=usuario_test.id,
        ocurrido_en=datetime.now(),
    )

    # Service created notification
    assert isinstance(notificacion, Notificacion)
    assert notificacion.id is not None

    # Registry lookup yields correct config
    config = get_event_config(
        AmbitoNotificacion.SOLICITUD, EventoNotificacion.ASIGNACION_CREADA
    )
    assert config is not None
    assert config.categoria == CategoriaNotificacion.INSTITUCIONAL
    assert config.default_audiencia == AmbitoAudience.AREA

    # Notification matches event registered in registry
    assert (
        notificacion.evento
        == EventoNotificacion.ASIGNACION_CREADA
        == EventoNotificacion.ASIGNACION_CREADA
    )
