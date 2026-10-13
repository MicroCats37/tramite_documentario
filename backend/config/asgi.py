"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi = get_asgi_application()

# WebSocket URL patterns
from modules.notificaciones.routing import websocket_urlpatterns

# JWT cookie middleware for WebSocket (must be inside AllowedHostsOriginValidator)
from core.middleware.jwt_cookie_websocket import JWTOKCookieMiddleware

application = ProtocolTypeRouter(
    {
        "http": django_asgi,
        "websocket": AllowedHostsOriginValidator(
            # JWTOKCookieMiddleware validates JWT httpOnly cookie and sets scope['user']
            # AuthMiddlewareStack provides Django session user as fallback
            AuthMiddlewareStack(
                JWTOKCookieMiddleware(
                    URLRouter(websocket_urlpatterns)
                )
            )
        ),
    }
)
