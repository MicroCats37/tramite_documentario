"""
WebSocket consumer for real-time notifications.

This consumer:
- Authenticates the user via JWT cookie (validated by JWTOKCookieMiddleware)
- Joins the user-specific group: notifications.user.<user_id>
- Receives notification events from the channel layer and sends them to the WebSocket

Group naming: notifications.user.{user.id}

No database queries, no business logic — pure channel layer relay.
"""

from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user-specific notification delivery.

    Authentication:
        - Validates JWT access token from httpOnly cookie via JWTOKCookieMiddleware
        - If scope['user'] is not authenticated, closes the connection

    Groups:
        - Each connected user joins: notifications.user.<user.id>
        - Services send to this group; this consumer relays to the WebSocket

    Workflow:
        1. connect:    authenticate, join group, accept
        2. receive:    (not used — push only)
        3. disconnect: leave group
    """

    async def connect(self):
        """Accept WebSocket connection if user is authenticated."""
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            # 4401 = custom "unauthenticated" — manager must NOT auto-reconnect
            await self.close(code=4401)
            return

        self.user = user
        self.group_name = f"notifications.user.{user.id}"

        # Join the user-specific notification group
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        """Leave the notification group on disconnect."""
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # ── Group message handlers ─────────────────────────────────────────

    async def notification_created(self, event):
        """
        Handle 'notification.created' group messages.

        event payload:
            {
                "type": "notification.created",
                "notification_id": <int>,
                "titulo": <str>,
                "mensaje": <str>,
                "prioridad": <str>,
                "created_at": <str ISO>,
            }

        Relays the notification data to the WebSocket as JSON string.
        """
        import json

        await self.send(
            text_data=json.dumps({
                "type": "notification.created",
                **{k: v for k, v in event.items() if k != "type"},
            })
        )

    async def notification_read(self, event):
        """
        Handle 'notification.read' group messages.

        event payload:
            {
                "type": "notification.read",
                "notification_id": <int>,
            }
        """
        import json

        await self.send(
            text_data=json.dumps({
                "type": "notification.read",
                **{k: v for k, v in event.items() if k != "type"},
            })
        )
