"""
ASGI middleware for WebSocket JWT authentication via httpOnly cookie.

Extracts the access_token from a cookie, validates it, and populates
scope['user'] with the authenticated user — same secret/algorithm as ninja_jwt.

Cookie name: derived from settings.NINJA_JWT['WS_COOKIE_NAME'], which is
configured in base.py from the AUTH_STORAGE_PREFIX env var as
f"{AUTH_STORAGE_PREFIX}_access_token". Must match the frontend cookie
name (which uses NEXT_PUBLIC_AUTH_STORAGE_PREFIX with the same prefix).

Validation approach:
- JWT cryptographic validation: signature + expiry via jwt.decode() (same secret/algorithm as ninja_jwt)
- User resolution: TokenUser from ninja_jwt.state (no DB access required in handshake)

The consumer checks scope['user'].is_authenticated and closes if not authenticated.
"""

import jwt

from django.contrib.auth.models import AnonymousUser


class JWTTokenUser:
    """
    Lightweight user-like object created from a validated JWT payload.

    Provides just enough of Django's user interface for the consumer
    to verify authentication and access the user_id from the token.

    Does NOT require database access.
    """

    def __init__(self, payload: dict):
        self._payload = payload
        self.id = payload.get("user_id")
        # Django's AnonymousUser has is_authenticated = False
        # We set True so the consumer accepts the connection
        self.is_authenticated = True
        self.is_active = True
        self.is_staff = payload.get("is_staff", False)
        self.is_superuser = payload.get("is_superuser", False)

    def __str__(self):
        return f"JWTTokenUser(id={self.id})"


def _parse_cookie_header(cookie_header: bytes | str) -> dict[str, str]:
    """
    Parse a Cookie header value into a dict of {name: value}.

    Handles both bytes (ASGI headers) and str.
    """
    if isinstance(cookie_header, bytes):
        cookie_header = cookie_header.decode("latin-1")

    result = {}
    for part in cookie_header.split(";"):
        part = part.strip()
        if "=" in part:
            name, _, value = part.partition("=")
            result[name.strip()] = value.strip()
    return result


class JWTOKCookieMiddleware:
    """
    ASGI middleware that authenticates WebSocket connections via JWT httpOnly cookie.

    Reads the access_token cookie from the WebSocket handshake headers,
    validates the JWT, and populates scope['user'] with a TokenUser.

    Usage:
        application = ProtocolTypeRouter({
            "websocket": AllowedHostsOriginValidator(
                JWTOKCookieMiddleware(URLRouter(websocket_urlpatterns))
            ),
        })

    If validation fails, scope['user'] is set to AnonymousUser.
    The consumer should check scope['user'].is_authenticated and close if not.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "websocket":
            await self.app(scope, receive, send)
            return

        # Extract cookie name from settings — must be configured via
        # AUTH_STORAGE_PREFIX env var in base.py (NINJA_JWT['WS_COOKIE_NAME']).
        from django.conf import settings

        ninja_jwt_settings = getattr(settings, "NINJA_JWT", {})
        cookie_name = ninja_jwt_settings.get("WS_COOKIE_NAME")
        if not cookie_name:
            raise RuntimeError(
                "NINJA_JWT['WS_COOKIE_NAME'] is not configured. "
                "Set AUTH_STORAGE_PREFIX env var in your .env file. "
                "See .env.example for documentation."
            )

        # Parse cookies from headers
        cookies: dict[str, str] = {}
        headers = dict(scope.get("headers", []))
        cookie_header = headers.get(b"cookie", b"")
        if cookie_header:
            cookies = _parse_cookie_header(cookie_header)

        # Extract access token from cookie
        token = cookies.get(cookie_name)

        user = AnonymousUser()
        if token:
            user = self._validate_token(token)

        # Attach user to scope — consumer can check scope['user'].is_authenticated
        scope["user"] = user

        await self.app(scope, receive, send)

    def _validate_token(self, token: str) -> AnonymousUser | JWTTokenUser:
        """
        Validate a JWT access token and return a JWTTokenUser.

        Uses the same secret/algorithm as ninja_jwt.
        Returns AnonymousUser if validation fails.
        """
        try:
            from django.conf import settings

            ninja_jwt_settings = getattr(settings, "NINJA_JWT", {})
            secret_key = settings.SECRET_KEY
            algorithm = ninja_jwt_settings.get("ALGORITHM", "HS256")

            # Decode and verify the token (verifies signature + exp automatically)
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=[algorithm],
                options={"verify_exp": True},
            )

            # Create a JWTTokenUser from the validated payload (no DB access)
            if not payload.get("user_id"):
                return AnonymousUser()

            return JWTTokenUser(payload)

        except Exception:
            # Any validation error → treat as anonymous
            return AnonymousUser()
