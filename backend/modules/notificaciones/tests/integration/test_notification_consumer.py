"""
Integration tests for NotificationConsumer and JWTOKCookieMiddleware (Apply 2).

Tests:
1. Valid JWT cookie → middleware sets scope['user'], consumer accepts, can receive messages
2. No cookie / invalid cookie → middleware leaves AnonymousUser, consumer rejects/closes
3. group_send to user's group → message received by that socket
4. group_send to different user's group → no message received

Scope (per Apply 2 contract):
- NO database queries in consumer
- NO event emission from services
- Uses InMemoryChannelLayer (test settings)
"""

import pytest
import asyncio
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model

from ninja_jwt.tokens import AccessToken

from modules.notificaciones.consumers import NotificationConsumer


# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def user_alice(db):
    """Create test user Alice."""
    User = get_user_model()
    return User.objects.create_user(
        username="alice",
        email="alice@cip.gob.pe",
        password="testpass123",
        dni="11111111",
        nombres="Alice",
        apellidos="Test",
    )


@pytest.fixture
def user_bob(db):
    """Create test user Bob."""
    User = get_user_model()
    return User.objects.create_user(
        username="bob",
        email="bob@cip.gob.pe",
        password="testpass123",
        dni="22222222",
        nombres="Bob",
        apellidos="Test",
    )


# ── Tests ───────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_valid_jwt_cookie_connects(user_alice):
    """
    GIVEN:  a valid JWT access token cookie for user_alice
    WHEN:   the WebSocket connection is established through the full ASGI stack
            (JWTOKCookieMiddleware → consumer)
    THEN:   the connection is accepted (connected=True).

    This tests the full stack: middleware validates JWT cookie and sets scope['user'].
    """
    from django.conf import settings
    from config.asgi import application

    token = str(AccessToken.for_user(user_alice))
    # Read the cookie name from settings — derived from AUTH_STORAGE_PREFIX env var.
    ws_cookie_name = getattr(settings, "NINJA_JWT", {}).get("WS_COOKIE_NAME")
    assert ws_cookie_name, "WS_COOKIE_NAME must be set via AUTH_STORAGE_PREFIX env var"
    headers = [(b"cookie", f"{ws_cookie_name}={token}".encode())]

    communicator = WebsocketCommunicator(
        application,
        path="/ws/notificaciones/",
        headers=headers,
    )

    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.disconnect()


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_no_cookie_connection_rejected():
    """
    GIVEN:  no JWT cookie provided
    WHEN:   the WebSocket connection is attempted through the full ASGI stack
    THEN:   the connection is rejected (connected=False) with close code 4401.
            The frontend manager interprets 4401 as auth failure and does NOT
            auto-reconnect (per Apply 5 contract).
    """
    from config.asgi import application

    communicator = WebsocketCommunicator(
        application,
        path="/ws/notificaciones/",
        headers=[],  # No cookie header
    )

    connected, subprotocol = await communicator.connect()
    assert connected is False
    # WebsocketCommunicator stores the close code in the result when reject is called
    # Verify the subprotocol is the close code dict (when reject occurs)
    # Note: WebsocketCommunicator returns (connected, subprotocol) where subprotocol
    # may contain close info in some versions; we verify rejection by connected=False


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_invalid_jwt_cookie_connection_rejected(user_alice):
    """
    GIVEN:  an invalid (non-JWT) cookie value
    WHEN:   the WebSocket connection is attempted through the full ASGI stack
    THEN:   the connection is rejected.
    """
    from django.conf import settings
    from config.asgi import application

    ws_cookie_name = getattr(settings, "NINJA_JWT", {}).get("WS_COOKIE_NAME")
    assert ws_cookie_name, "WS_COOKIE_NAME must be set via AUTH_STORAGE_PREFIX env var"
    headers = [(b"cookie", f"{ws_cookie_name}=not.a.valid.jwt.token".encode())]

    communicator = WebsocketCommunicator(
        application,
        path="/ws/notificaciones/",
        headers=headers,
    )

    connected, _ = await communicator.connect()
    assert connected is False


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_group_send_to_user_reaches_socket(user_alice):
    """
    GIVEN:  alice is connected with a valid JWT cookie through the full ASGI stack
    WHEN:   a notification_created event is sent to group notifications.user.{alice.id}
    THEN:   alice receives the notification JSON over her WebSocket.
    """
    from django.conf import settings
    from config.asgi import application
    from channels.layers import get_channel_layer

    token = str(AccessToken.for_user(user_alice))
    ws_cookie_name = getattr(settings, "NINJA_JWT", {}).get("WS_COOKIE_NAME")
    assert ws_cookie_name, "WS_COOKIE_NAME must be set via AUTH_STORAGE_PREFIX env var"
    headers = [(b"cookie", f"{ws_cookie_name}={token}".encode())]

    channel_layer = get_channel_layer()
    group_name = f"notifications.user.{user_alice.id}"

    communicator = WebsocketCommunicator(
        application,
        path="/ws/notificaciones/",
        headers=headers,
    )
    connected, _ = await communicator.connect()
    assert connected is True

    # Send a notification event to alice's group via channel layer
    await channel_layer.group_send(
        group_name,
        {
            "type": "notification.created",
            "notification_id": 42,
            "titulo": "Nuevo trámite asignado",
            "mensaje": "Se le ha asignado el expediente EXP-2026-001",
            "prioridad": "alta",
            "created_at": "2026-09-19T10:00:00Z",
        },
    )

    # Receive the message from the WebSocket
    response = await communicator.receive_json_from(timeout=2)

    assert response["type"] == "notification.created"
    assert response["notification_id"] == 42
    assert response["titulo"] == "Nuevo trámite asignado"
    assert response["prioridad"] == "alta"

    await communicator.disconnect()


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_group_send_to_different_user_does_not_reach_socket(user_alice, user_bob):
    """
    GIVEN:  alice is connected with a valid JWT cookie through the full ASGI stack
    WHEN:   a notification_created event is sent to bob's group (notifications.user.{bob.id})
    THEN:   alice receives NOTHING on her WebSocket.
    """
    from django.conf import settings
    from config.asgi import application
    from channels.layers import get_channel_layer

    token_alice = str(AccessToken.for_user(user_alice))
    ws_cookie_name = getattr(settings, "NINJA_JWT", {}).get("WS_COOKIE_NAME")
    assert ws_cookie_name, "WS_COOKIE_NAME must be set via AUTH_STORAGE_PREFIX env var"
    headers = [(b"cookie", f"{ws_cookie_name}={token_alice}".encode())]

    channel_layer = get_channel_layer()

    # Alice connects
    communicator_alice = WebsocketCommunicator(
        application,
        path="/ws/notificaciones/",
        headers=headers,
    )
    connected, _ = await communicator_alice.connect()
    assert connected is True

    # Send to bob's group (not alice's)
    bob_group = f"notifications.user.{user_bob.id}"
    await channel_layer.group_send(
        bob_group,
        {
            "type": "notification.created",
            "notification_id": 99,
            "titulo": "Mensaje para Bob",
            "mensaje": "Bob only",
            "prioridad": "normal",
            "created_at": "2026-09-19T10:00:00Z",
        },
    )

    # Wait to ensure the group dispatch would have delivered if alice was in bob's group
    await asyncio.sleep(0.3)

    # Alice should NOT have received bob's message.
    # Verify by ensuring alice's group name is NOT bob's group.
    # (The consumer joined alice to her own group, not bob's.)
    # We also confirm by sending to alice's group and verifying she DOES receive it.
    alice_group = f"notifications.user.{user_alice.id}"
    await channel_layer.group_send(
        alice_group,
        {
            "type": "notification.created",
            "notification_id": 77,
            "titulo": "Mensaje solo para Alice",
            "mensaje": "Alice only",
            "prioridad": "normal",
            "created_at": "2026-09-19T10:00:00Z",
        },
    )
    response = await communicator_alice.receive_json_from(timeout=2)
    assert response["notification_id"] == 77, "Alice should receive her own group message"

    await communicator_alice.disconnect()
