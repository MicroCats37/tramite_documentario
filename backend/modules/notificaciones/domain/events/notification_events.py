"""
Domain events for real-time notification system.

Defines the structure of events emitted over WebSocket channels.
Following the SDD contract for notification.created events.

Event schema (version 1):
    {
        "type": "notification.created",
        "notification_id": "uuid",      # string UUID for JSON compatibility
        "occurred_at": "ISO8601",       # ISO8601 timestamp
        "version": 1                    # event schema version
    }
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from uuid import UUID


EVENT_TYPE_NOTIFICATION_CREATED = "notification.created"
CURRENT_EVENT_VERSION = 1


@dataclass(frozen=True)
class NotificationCreatedEvent:
    """
    Immutable value object representing a notification.created event.

    Attributes:
        notification_id: UUID of the created notification (stored as string for JSON).
        occurred_at: ISO8601 timestamp when the event occurred.
        version: Event schema version (currently 1).
    """
    notification_id: str
    occurred_at: str
    version: int = CURRENT_EVENT_VERSION

    @property
    def type(self) -> str:
        return EVENT_TYPE_NOTIFICATION_CREATED

    def to_dict(self) -> dict:
        """
        Convert to dict for channel layer group_send.

        Returns:
            Dict with type, notification_id, occurred_at, version.
        """
        return {
            "type": self.type,
            "notification_id": self.notification_id,
            "occurred_at": self.occurred_at,
            "version": self.version,
        }

    @classmethod
    def create(cls, notification_id: UUID, occurred_at: datetime | None = None) -> "NotificationCreatedEvent":
        """
        Factory to create a NotificationCreatedEvent.

        Args:
            notification_id: UUID of the notification.
            occurred_at: Event timestamp (defaults to now UTC).

        Returns:
            NotificationCreatedEvent instance.
        """
        if occurred_at is None:
            occurred_at = datetime.now(timezone.utc)
        return cls(
            notification_id=str(notification_id),
            occurred_at=occurred_at.isoformat(),
        )


def build_notification_created_event(
    notification_id: UUID,
    occurred_at: datetime | None = None,
) -> dict:
    """
    Build a notification.created event dict for channel layer group_send.

    Args:
        notification_id: UUID of the notification.
        occurred_at: Event timestamp (defaults to now UTC).

    Returns:
        Dict suitable for channel layer group_send payload.
    """
    return NotificationCreatedEvent.create(notification_id, occurred_at).to_dict()
