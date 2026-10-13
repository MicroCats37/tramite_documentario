"""
WebSocket URL routing for the notificaciones module.

Route: /ws/notificaciones/

The consumer (NotificationConsumer) authenticates via JWT httpOnly cookie
through the JWTOKCookieMiddleware stacked in config.asgi.
"""

from django.urls import re_path

from .consumers import NotificationConsumer

websocket_urlpatterns = [
    re_path(r"^ws/notificaciones/$", NotificationConsumer.as_asgi()),
]
