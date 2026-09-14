"""
Integration tests for GET /usuarios/mencionables/ endpoint.

Tests:
- list mencionables by solicitud_id returns users assigned to solicitud areas
- q filters results
- response is non-paginated list
- conversacion_id derives solicitud
- area_id alone works

Uses TestAsyncClient with async def tests (per conversaciones pattern).
"""

import uuid
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from ninja_extra.testing import TestAsyncClient
from ninja_jwt.tokens import AccessToken

from config.api import api
from modules.usuarios.domain.models import Area, AsignacionUsuario, Cargo
from modules.asignaciones.domain.models import (
    SolicitudAsignacion,
    SolicitudAsignacionPeriodo,
    SolicitudAsignacionUsuario,
)
from modules.tramites.domain.models import Solicitud, Expediente
from modules.conversaciones.domain.models import Conversacion, SolicitudConversacion


pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.asyncio]


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
async def cargo(db):
    """A cargo for assignments."""
    return await Cargo.objects.acreate(
        nombre="Cargo de Prueba",
        activo=True,
    )


@pytest.fixture
async def area(db):
    """An active area."""
    return await Area.objects.acreate(
        nombre="Área de Prueba",
        descripcion="Descripción",
        activo=True,
    )


@pytest.fixture
async def area_2(db):
    """A second active area."""
    return await Area.objects.acreate(
        nombre="Área Segunda",
        descripcion="Descripción 2",
        activo=True,
    )


@pytest.fixture
async def usuario(db):
    """A test usuario."""
    User = get_user_model()
    return await User.objects.acreate(
        username="12345678",
        email="test@cip.gob.pe",
        password="testpass123",
        dni="12345678",
        nombres="Usuario",
        apellidos="Test",
    )


@pytest.fixture
async def usuario_2(db):
    """A second test usuario."""
    User = get_user_model()
    return await User.objects.acreate(
        username="87654321",
        email="test2@cip.gob.pe",
        password="testpass123",
        dni="87654321",
        nombres="Segundo",
        apellidos="Usuario",
    )


@pytest.fixture
async def usuario_3(db):
    """A third test usuario."""
    User = get_user_model()
    return await User.objects.acreate(
        username="11223344",
        email="test3@cip.gob.pe",
        password="testpass123",
        dni="11223344",
        nombres="Carlos",
        apellidos="Otro",
    )


@pytest.fixture
async def asignacion_activa(db, usuario, area, cargo):
    """Active assignment for usuario to area."""
    return await AsignacionUsuario.objects.acreate(
        usuario=usuario,
        area=area,
        cargo=cargo,
        periodo_inicio=date.today(),
        periodo_fin=None,
    )


@pytest.fixture
async def asignacion_activa_2(db, usuario_2, area_2, cargo):
    """Active assignment for usuario_2 to area_2."""
    return await AsignacionUsuario.objects.acreate(
        usuario=usuario_2,
        area=area_2,
        cargo=cargo,
        periodo_inicio=date.today(),
        periodo_fin=None,
    )


@pytest.fixture
async def asignacion_inactiva(db, usuario_3, area, cargo):
    """Inactive assignment (periodo_fin set)."""
    return await AsignacionUsuario.objects.acreate(
        usuario=usuario_3,
        area=area,
        cargo=cargo,
        periodo_inicio=date.today(),
        periodo_fin=date.today(),
    )


@pytest.fixture
async def expediente(db, usuario):
    """A test expediente."""
    from modules.tramites.domain.constants import TipoPersona
    from modules.tramites.domain.models import TipoDocumento

    tipo_doc = await TipoDocumento.objects.afirst()
    if tipo_doc is None:
        tipo_doc = await TipoDocumento.objects.acreate(
            nombre="Solicitud General",
            activo=True,
        )

    return await Expediente.objects.acreate(
        tipo_persona=TipoPersona.NATURAL,
        tipo_documento=tipo_doc,
        numero=1,
        asunto="Asunto de prueba",
        fecha_registro=date.today(),
        creado_por=usuario,
    )


@pytest.fixture
async def solicitud(db, expediente, usuario):
    """A test solicitud."""
    from modules.tramites.domain.constants import EstadoSolicitud, Prioridad

    return await Solicitud.objects.acreate(
        expediente=expediente,
        estado=EstadoSolicitud.REGISTRADA,
        prioridad=Prioridad.MEDIA,
        fecha_registro=date.today(),
        creado_por=usuario,
    )


@pytest.fixture
async def solicitud_asignacion(db, solicitud, area):
    """SolicitudAsignacion linking solicitud to area."""
    return await SolicitudAsignacion.objects.acreate(
        solicitud=solicitud,
        area=area,
        fecha_incorporacion=date.today(),
    )


@pytest.fixture
async def solicitud_asignacion_2(db, solicitud, area_2):
    """SolicitudAsignacion linking solicitud to area_2."""
    return await SolicitudAsignacion.objects.acreate(
        solicitud=solicitud,
        area=area_2,
        fecha_incorporacion=date.today(),
    )


@pytest.fixture
async def conversacion(db, usuario):
    """A test conversacion."""
    return await Conversacion.objects.acreate(
        titulo="Conversación de prueba",
        creada_por=usuario,
    )


@pytest.fixture
async def solicitud_conversacion(db, solicitud, conversacion):
    """Bridge linking solicitud to conversacion."""
    return await SolicitudConversacion.objects.acreate(
        solicitud=solicitud,
        conversacion=conversacion,
    )


# ── Auth helper ────────────────────────────────────────────────────────────────

@pytest.fixture
async def auth_client(db, usuario):
    """Async test client with JWT auth."""
    token = str(AccessToken.for_user(usuario))
    client = TestAsyncClient(api)
    headers = {"Authorization": f"Bearer {token}"}
    client.headers.update(headers)
    return client


# ── Tests ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_listar_mencionables_por_solicitud(
    usuario, usuario_2, area, area_2, asignacion_activa, asignacion_activa_2,
    solicitud, solicitud_asignacion, solicitud_asignacion_2, auth_client,
):
    """
    GIVEN:  two areas assigned to a solicitud, each with an active user assignment
    WHEN:   GET /usuarios/mencionables/?solicitud_id={id} is called
    THEN:   response status is 200
             AND both users are returned (non-paginated list)
             AND response is a simple list inside ApiResponse (no pagination)
    """
    response = await auth_client.get(
        f"/usuarios/mencionables/?solicitud_id={solicitud.id}"
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()

    assert data["success"] is True
    assert "data" in data
    # Non-paginated: data is a list, not {items, total, ...}
    assert isinstance(data["data"], list), "data should be a non-paginated list"

    user_ids = {u["id"] for u in data["data"]}
    assert str(usuario.id) in user_ids
    assert str(usuario_2.id) in user_ids


@pytest.mark.asyncio
async def test_listar_mencionables_solo_activos(
    usuario, usuario_3, area, asignacion_activa, asignacion_inactiva,
    solicitud, solicitud_asignacion, auth_client,
):
    """
    GIVEN:  one active and one inactive user assignment to the solicitud's area
    WHEN:   GET /usuarios/mencionables/?solicitud_id={id} is called
    THEN:   only the user with active assignment is returned
    """
    response = await auth_client.get(
        f"/usuarios/mencionables/?solicitud_id={solicitud.id}"
    )

    assert response.status_code == 200

    data = response.json()
    user_ids = {u["id"] for u in data["data"]}

    assert str(usuario.id) in user_ids
    assert str(usuario_3.id) not in user_ids


@pytest.mark.asyncio
async def test_listar_mencionables_filtro_nombre(
    usuario, usuario_2, area, area_2, asignacion_activa, asignacion_activa_2,
    solicitud, solicitud_asignacion, auth_client,
):
    """
    GIVEN:  two mentionable users exist
    WHEN:   GET /usuarios/mencionables/?solicitud_id={id}&nombre=Usuario is called
    THEN:   only users matching 'Usuario' in nombres/apellidos/username/dni are returned
    """
    response = await auth_client.get(
        f"/usuarios/mencionables/?solicitud_id={solicitud.id}&nombre=Usuario"
    )

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1
    for u in data["data"]:
        q_lower = "usuario"
        assert (
            q_lower in (u["nombres"] or "").lower()
            or q_lower in (u["apellidos"] or "").lower()
            or q_lower in (u["username"] or "").lower()
        )


@pytest.mark.asyncio
async def test_listar_mencionables_por_conversacion_id(
    usuario, area, asignacion_activa,
    solicitud, solicitud_asignacion, conversacion, solicitud_conversacion, auth_client,
):
    """
    GIVEN:  a conversacion linked to a solicitud which has area assignments
    WHEN:   GET /usuarios/mencionables/?conversacion_id={id} is called
    THEN:   users assigned to the solicitud's areas are returned
    """
    response = await auth_client.get(
        f"/usuarios/mencionables/?conversacion_id={conversacion.id}"
    )

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["data"], list)
    user_ids = {u["id"] for u in data["data"]}
    assert str(usuario.id) in user_ids


@pytest.mark.asyncio
async def test_listar_mencionables_por_area_id(
    usuario, area, asignacion_activa, auth_client,
):
    """
    GIVEN:  a user assigned to an area
    WHEN:   GET /usuarios/mencionables/?area_id={id} is called
    THEN:   users assigned to that area are returned
    """
    response = await auth_client.get(f"/usuarios/mencionables/?area_id={area.id}")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["data"], list)
    user_ids = {u["id"] for u in data["data"]}
    assert str(usuario.id) in user_ids


@pytest.mark.asyncio
async def test_listar_mencionables_sin_contexto_devuelve_vacio(usuario, auth_client):
    """
    GIVEN:  a user exists
    WHEN:   GET /usuarios/mencionables/ is called without any context param
    THEN:   response status is 200 with empty list
    """
    response = await auth_client.get("/usuarios/mencionables/")

    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 0


@pytest.mark.asyncio
async def test_listar_mencionables_usuario_inactivo_no_devuelto(
    db, area, asignacion_activa, usuario, usuario_2, auth_client, cargo,
):
    """
    GIVEN:  an active user and an inactive (is_active=False) user assigned to an area
    WHEN:   GET /usuarios/mencionables/?area_id={id} is called
    THEN:   only the active user is returned
    """
    # usuario_2 will be inactive
    usuario_2.is_active = False
    await usuario_2.asave()

    await AsignacionUsuario.objects.acreate(
        usuario=usuario_2,
        area=area,
        cargo=cargo,
        periodo_inicio=date.today(),
        periodo_fin=None,
    )

    response = await auth_client.get(f"/usuarios/mencionables/?area_id={area.id}")

    assert response.status_code == 200

    data = response.json()
    user_ids = {u["id"] for u in data["data"]}
    assert str(usuario.id) in user_ids
    assert str(usuario_2.id) not in user_ids


@pytest.mark.asyncio
async def test_listar_mencionables_no_autenticado(db, area):
    """
    GIVEN:  no authenticated user
    WHEN:   GET /usuarios/mencionables/?area_id={id} is called
    THEN:   response status is 401 or 403
    """
    client = TestAsyncClient(api)
    fake_id = uuid.uuid4()
    response = await client.get(f"/usuarios/mencionables/?area_id={fake_id}")

    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_listar_mencionables_conversacion_no_existe(usuario, auth_client):
    """
    GIVEN:  no bridge exists for the conversacion
    WHEN:   GET /usuarios/mencionables/?conversacion_id={fake} is called
    THEN:   response status is 200 with empty list
    """
    fake_id = uuid.uuid4()

    response = await auth_client.get(
        f"/usuarios/mencionables/?conversacion_id={fake_id}"
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 0


# ── Tests: SolicitudAsignacionUsuario path (solicitud_id context) ───────────────


@pytest.fixture
async def solicitud_asignacion_periodo_abierto(db, solicitud_asignacion):
    """Open period for the solicitud-asignacion (fecha_fin=null)."""
    from datetime import datetime, timezone

    return await SolicitudAsignacionPeriodo.objects.acreate(
        asignacion=solicitud_asignacion,
        numero_ciclo=1,
        tipo_participacion="PRINCIPAL",
        estado="EN_GESTION",
        fecha_inicio=datetime.now(timezone.utc),
        fecha_fin=None,
    )


@pytest.fixture
async def solicitud_asignacion_periodo_cerrado(db, solicitud_asignacion):
    """Closed period for the solicitud-asignacion (fecha_fin set)."""
    from datetime import datetime, timezone

    return await SolicitudAsignacionPeriodo.objects.acreate(
        asignacion=solicitud_asignacion,
        numero_ciclo=2,
        tipo_participacion="PRINCIPAL",
        estado="CERRADO",
        fecha_inicio=datetime.now(timezone.utc),
        fecha_fin=datetime.now(timezone.utc),
    )


@pytest.fixture
async def participante_activo(db, usuario, solicitud_asignacion_periodo_abierto):
    """Active participant in an open period."""
    from datetime import datetime, timezone

    return await SolicitudAsignacionUsuario.objects.acreate(
        periodo=solicitud_asignacion_periodo_abierto,
        usuario=usuario,
        rol="Responsable",
        fecha_inicio=datetime.now(timezone.utc),
        fecha_fin=None,
    )


@pytest.fixture
async def participante_activo_area2(db, usuario_2, area_2, solicitud_asignacion_2):
    """Active participant (usuario_2) in an open period of area_2."""
    from datetime import datetime, timezone

    periodo_area2 = await SolicitudAsignacionPeriodo.objects.acreate(
        asignacion=solicitud_asignacion_2,
        numero_ciclo=1,
        tipo_participacion="PRINCIPAL",
        estado="EN_GESTION",
        fecha_inicio=datetime.now(timezone.utc),
        fecha_fin=None,
    )
    return await SolicitudAsignacionUsuario.objects.acreate(
        periodo=periodo_area2,
        usuario=usuario_2,
        rol="Colaborador",
        fecha_inicio=datetime.now(timezone.utc),
        fecha_fin=None,
    )


@pytest.fixture
async def participante_inactivo(db, usuario_3, solicitud_asignacion_periodo_abierto):
    """Inactive participant (fecha_fin set) in an open period."""
    from datetime import datetime, timezone

    return await SolicitudAsignacionUsuario.objects.acreate(
        periodo=solicitud_asignacion_periodo_abierto,
        usuario=usuario_3,
        rol="Revisor",
        fecha_inicio=datetime.now(timezone.utc),
        fecha_fin=datetime.now(timezone.utc),
    )


@pytest.fixture
async def participante_en_periodo_cerrado(db, usuario, solicitud_asignacion_periodo_cerrado):
    """Participant in a closed period — should NOT be returned."""
    from datetime import datetime, timezone

    return await SolicitudAsignacionUsuario.objects.acreate(
        periodo=solicitud_asignacion_periodo_cerrado,
        usuario=usuario,
        rol="Responsable",
        fecha_inicio=datetime.now(timezone.utc),
        fecha_fin=None,
    )


@pytest.mark.asyncio
async def test_solicitud_id_retorna_participantes_activos_periodos_abiertos(
    db,
    usuario,
    usuario_2,
    solicitud,
    solicitud_asignacion,
    solicitud_asignacion_2,
    solicitud_asignacion_periodo_abierto,
    participante_activo,
    participante_activo_area2,
    auth_client,
):
    """
    GIVEN:  two areas with open periods, each with an active participant
    WHEN:   GET /usuarios/mencionables/?solicitud_id={id} is called
    THEN:   both participants are returned
             AND response includes area_id, area_nombre, rol, periodo_id, numero_ciclo, tipo_participacion
    """
    response = await auth_client.get(
        f"/usuarios/mencionables/?solicitud_id={solicitud.id}"
    )

    assert response.status_code == 200, f"Got {response.status_code}: {response.content}"
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

    user_ids = {u["id"] for u in data["data"]}
    assert str(usuario.id) in user_ids
    assert str(usuario_2.id) in user_ids

    # Verify context fields are present
    for u in data["data"]:
        assert u["area_id"] is not None
        assert u["area_nombre"] is not None
        assert u["rol"] is not None
        assert u["periodo_id"] is not None
        assert u["numero_ciclo"] is not None
        assert u["tipo_participacion"] in ("PRINCIPAL", "ADJUNTA")


@pytest.mark.asyncio
async def test_periodos_cerrados_excluidos(
    db,
    usuario,
    solicitud,
    solicitud_asignacion,
    solicitud_asignacion_periodo_abierto,
    solicitud_asignacion_periodo_cerrado,
    participante_en_periodo_cerrado,
    auth_client,
):
    """
    GIVEN:  a participant only in a closed period (no active participation in open periods)
    WHEN:   GET /usuarios/mencionables/?solicitud_id={id} is called
    THEN:   that participant is NOT returned
    """
    response = await auth_client.get(
        f"/usuarios/mencionables/?solicitud_id={solicitud.id}"
    )

    assert response.status_code == 200
    data = response.json()
    user_ids = {u["id"] for u in data["data"]}
    assert str(usuario.id) not in user_ids


@pytest.mark.asyncio
async def test_participante_fecha_fin_set_excluido(
    db,
    usuario,
    usuario_3,
    solicitud,
    solicitud_asignacion,
    solicitud_asignacion_periodo_abierto,
    participante_activo,
    participante_inactivo,
    auth_client,
):
    """
    GIVEN:  an active participant and an inactive participant (fecha_fin set)
            in the same open period
    WHEN:   GET /usuarios/mencionables/?solicitud_id={id} is called
    THEN:   only the active participant is returned
    """
    response = await auth_client.get(
        f"/usuarios/mencionables/?solicitud_id={solicitud.id}"
    )

    assert response.status_code == 200
    data = response.json()
    user_ids = {u["id"] for u in data["data"]}
    assert str(usuario.id) in user_ids
    assert str(usuario_3.id) not in user_ids


@pytest.mark.asyncio
async def test_periodo_id_estrecha_resultados(
    db,
    usuario,
    usuario_2,
    solicitud,
    solicitud_asignacion,
    solicitud_asignacion_2,
    solicitud_asignacion_periodo_abierto,
    participante_activo,
    participante_activo_area2,
    auth_client,
):
    """
    GIVEN:  two areas with open periods, each with an active participant
    WHEN:   GET /usuarios/mencionables/?solicitud_id={id}&periodo_id={periodo1_id} is called
    THEN:   only the participant of that specific period is returned
    """
    # Get the periodo_id of the first participant
    periodo_id = participante_activo.periodo_id

    response = await auth_client.get(
        f"/usuarios/mencionables/?solicitud_id={solicitud.id}&periodo_id={periodo_id}"
    )

    assert response.status_code == 200
    data = response.json()
    user_ids = {u["id"] for u in data["data"]}
    assert str(usuario.id) in user_ids
    assert str(usuario_2.id) not in user_ids

    # Verify the returned participant has the correct periodo_id in context
    returned_user = next(u for u in data["data"] if u["id"] == str(usuario.id))
    assert returned_user["periodo_id"] == str(periodo_id)


@pytest.mark.asyncio
async def test_solicitud_sin_participantes_retorna_vacio(
    db,
    usuario,
    solicitud,
    solicitud_asignacion,
    auth_client,
):
    """
    GIVEN:  a solicitud with areas assigned but no participants in any open period
    WHEN:   GET /usuarios/mencionables/?solicitud_id={id} is called
    THEN:   response is 200 with empty list (no fallback to global AsignacionUsuario)
    """
    response = await auth_client.get(
        f"/usuarios/mencionables/?solicitud_id={solicitud.id}"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 0


@pytest.mark.asyncio
async def test_area_id_usa_asignacion_usuario_global(
    db,
    usuario,
    area,
    asignacion_activa,
    auth_client,
):
    """
    GIVEN:  a user with an active global AsignacionUsuario to an area
    WHEN:   GET /usuarios/mencionables/?area_id={id} is called (no solicitud_id)
    THEN:   the user is returned with NO context fields (backward compat)
    """
    response = await auth_client.get(f"/usuarios/mencionables/?area_id={area.id}")

    assert response.status_code == 200
    data = response.json()
    user_ids = {u["id"] for u in data["data"]}
    assert str(usuario.id) in user_ids

    # No context fields for area_id path
    returned_user = next(u for u in data["data"] if u["id"] == str(usuario.id))
    assert returned_user["area_id"] is None
    assert returned_user["area_nombre"] is None
    assert returned_user["rol"] is None
    assert returned_user["periodo_id"] is None
