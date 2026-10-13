"""
Shared fixtures index for conversaciones tests.
"""
import pytest

from modules.conversaciones.tests.factories import (
    make_conversacion_payload,
    make_mensaje_payload,
    make_mensaje_archivo_adjunto_payload,
    make_mensaje_mencion_payload,
    make_solicitud_conversacion_payload,
)


# ── Fake Notification Publisher ────────────────────────────────────────────────


class FakeNotificationRealtimePublisher:
    """
    Fake publisher that records calls instead of sending to channel layer.

    Used to verify that NotificacionService calls the publisher correctly
    without requiring a real channel layer or network.
    """

    def __init__(self):
        self.calls: list[dict] = []

    def publish_created(self, user_id, notification_id, occurred_at=None):
        self.calls.append({
            "method": "publish_created",
            "user_id": user_id,
            "notification_id": notification_id,
            "occurred_at": occurred_at,
        })

    def publish_created_batch(self, user_ids, notification_id, occurred_at=None):
        for user_id in set(user_ids):
            self.publish_created(user_id, notification_id, occurred_at)

    def clear(self):
        self.calls.clear()


@pytest.fixture
def fake_notification_publisher():
    """Provide a fresh FakeNotificationRealtimePublisher for each test."""
    return FakeNotificationRealtimePublisher()
