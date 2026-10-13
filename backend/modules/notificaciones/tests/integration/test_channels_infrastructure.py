"""
Tests for Channels / ASGI infrastructure (Apply 1).

Scope: verifies that CHANNEL_LAYERS settings are loaded, the ASGI application
is importable, and Django check passes — WITHOUT implementing NotificationConsumer.

These are NOT consumer tests — consumer implementation is deferred to Apply 2+.
"""
import pytest


@pytest.mark.django_db
def test_channel_layers_configured(settings):
    """
    GIVEN: Django settings are loaded with CHANNEL_LAYERS
    WHEN:  CHANNEL_LAYERS is accessed
    THEN:  it is a dict with a 'default' key and a known BACKEND.
    """
    from django.conf import settings as django_settings

    assert hasattr(django_settings, "CHANNEL_LAYERS")
    assert "default" in django_settings.CHANNEL_LAYERS
    layer = django_settings.CHANNEL_LAYERS["default"]
    assert "BACKEND" in layer


@pytest.mark.django_db
def test_asgi_application_is_protocol_type_router(settings):
    """
    GIVEN: config.asgi.application is imported
    WHEN:  it is accessed
    THEN:  it is a ProtocolTypeRouter instance (channels.routing.ProtocolTypeRouter).
    """
    from config.asgi import application

    # ProtocolTypeRouter.__class__.__name__ == 'ProtocolTypeRouter'
    assert type(application).__name__ == "ProtocolTypeRouter"


@pytest.mark.django_db
def test_django_check_passes(settings):
    """
    GIVEN: test settings (InMemoryChannelLayer)
    WHEN:  django.core.management.call_command('check') is invoked
    THEN:  it returns without errors.
    """
    from django.core.management import call_command

    # Should not raise
    call_command("check")


@pytest.mark.django_db
def test_channel_layer_send_receive_inmemory(settings):
    """
    GIVEN: InMemoryChannelLayer (test settings)
    WHEN:  a message is sent via the channel layer
    THEN:  it can be received back on the same channel.
    """
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    channel_name = "test-channel-apply1"

    # Send a test message
    import asyncio

    async def _send_and_receive():
        await channel_layer.send(channel_name, {"type": "test.event", "text": "hello"})
        received = await channel_layer.receive(channel_name)
        return received

    result = asyncio.get_event_loop().run_until_complete(_send_and_receive())
    assert result["type"] == "test.event"
    assert result["text"] == "hello"
