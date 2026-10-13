"""
NotificationRealtimePublisher — emits real-time notification events via Channels.

Uses Django's transaction.on_commit() to defer emission until after the
database transaction commits successfully.

This implementation:
- Provides both sync (async_to_sync) and async (await) interfaces
- Handles absence of channel layer gracefully (logs warning)
- Does NOT query the database — receives user IDs from the caller
- Is safe to call from within atomic blocks (on_commit defers execution)

Location: follows django-app-architecture-contract: infrastructure/ = concrete
implementations touching external systems (Channels/Redis).
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from modules.notificaciones.domain.events.notification_events import (
    EVENT_TYPE_NOTIFICATION_CREATED,
    build_notification_created_event,
)

logger = logging.getLogger(__name__)

# Group name pattern — must match NotificationConsumer.connect
def user_channel_group(user_id: UUID | int) -> str:
    """Return the channel group name for a given user ID."""
    return f"notifications.user.{user_id}"


class NotificationRealtimePublisher:
    """
    Publishes real-time notification events to Channels groups.

    Each user connects to their personal group (notifications.user.{user_id}).
    The publisher sends events to those groups via the channel layer.

    Provides two interfaces:
    - publish_created: sync, for use from transaction.on_commit callbacks
    - publish_created_async: async, for use from async code (views, consumers, tests)

    Usage (sync, from on_commit):
        publisher = NotificationRealtimePublisher()
        publisher.publish_created(user_id=some_uuid, notification_id=notif_uuid)

    Usage (async):
        publisher = NotificationRealtimePublisher()
        await publisher.publish_created_async(user_id=some_uuid, notification_id=notif_uuid)
    """

    def publish_created(
        self,
        user_id: UUID | int,
        notification_id: UUID,
        occurred_at: datetime | None = None,
    ) -> None:
        """
        Synchronous publish — wraps async_to_sync for use from sync contexts
        (e.g., transaction.on_commit callbacks).

        Args:
            user_id: ID of the user to notify.
            notification_id: ID of the created notification.
            occurred_at: Optional timestamp (defaults to now UTC).
        """
        group_name = user_channel_group(user_id)
        event_payload = build_notification_created_event(notification_id, occurred_at)

        try:
            channel_layer = get_channel_layer()
        except Exception:
            logger.warning(
                "NotificationRealtimePublisher: no channel layer available. "
                "Skipping publish for notification_id=%s to user_id=%s",
                notification_id,
                user_id,
            )
            return

        if channel_layer is None:
            logger.warning(
                "NotificationRealtimePublisher: channel layer is None. "
                "Skipping publish for notification_id=%s to user_id=%s",
                notification_id,
                user_id,
            )
            return

        try:
            async_to_sync(channel_layer.group_send)(
                group_name,
                event_payload,
            )
            logger.debug(
                "Published notification.created: notification_id=%s to group=%s",
                notification_id,
                group_name,
            )
        except Exception as e:
            logger.error(
                "NotificationRealtimePublisher: failed to publish "
                "notification_id=%s to group=%s: %s",
                notification_id,
                group_name,
                e,
            )

    async def publish_created_async(
        self,
        user_id: UUID | int,
        notification_id: UUID,
        occurred_at: datetime | None = None,
    ) -> None:
        """
        Async publish — for use from async contexts (views, consumers, tests).

        Args:
            user_id: ID of the user to notify.
            notification_id: ID of the created notification.
            occurred_at: Optional timestamp (defaults to now UTC).
        """
        group_name = user_channel_group(user_id)
        event_payload = build_notification_created_event(notification_id, occurred_at)

        try:
            channel_layer = get_channel_layer()
        except Exception:
            logger.warning(
                "NotificationRealtimePublisher: no channel layer available. "
                "Skipping publish for notification_id=%s to user_id=%s",
                notification_id,
                user_id,
            )
            return

        if channel_layer is None:
            logger.warning(
                "NotificationRealtimePublisher: channel layer is None. "
                "Skipping publish for notification_id=%s to user_id=%s",
                notification_id,
                user_id,
            )
            return

        try:
            await channel_layer.group_send(
                group_name,
                event_payload,
            )
            logger.debug(
                "Published notification.created (async): notification_id=%s to group=%s",
                notification_id,
                group_name,
            )
        except Exception as e:
            logger.error(
                "NotificationRealtimePublisher: failed to publish (async) "
                "notification_id=%s to group=%s: %s",
                notification_id,
                group_name,
                e,
            )

    def publish_created_batch(
        self,
        user_ids: list[UUID | int],
        notification_id: UUID,
        occurred_at: datetime | None = None,
    ) -> None:
        """
        Publish a notification.created event to multiple users (sync).

        Deduplicates user_ids before publishing.

        Args:
            user_ids: List of user IDs to notify.
            notification_id: ID of the created notification.
            occurred_at: Optional timestamp (defaults to now UTC).
        """
        unique_user_ids = list(set(user_ids))
        for user_id in unique_user_ids:
            self.publish_created(user_id, notification_id, occurred_at)

    async def publish_created_batch_async(
        self,
        user_ids: list[UUID | int],
        notification_id: UUID,
        occurred_at: datetime | None = None,
    ) -> None:
        """
        Publish a notification.created event to multiple users (async).

        Deduplicates user_ids before publishing.

        Args:
            user_ids: List of user IDs to notify.
            notification_id: ID of the created notification.
            occurred_at: Optional timestamp (defaults to now UTC).
        """
        unique_user_ids = list(set(user_ids))
        for user_id in unique_user_ids:
            await self.publish_created_async(user_id, notification_id, occurred_at)
