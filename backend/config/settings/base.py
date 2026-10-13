"""
Base settings — compartidas por todos los entornos.
"""

import environ
from pathlib import Path
from datetime import timedelta

# ── Paths ────────────────────────────────────────────────────
# Como base.py está en config/settings/base.py, subimos 3 niveles para llegar a la raíz
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── Environ ──────────────────────────────────────────────────
env = environ.Env(DEBUG=(bool, False))
# Lee .env si existe (para desarrollo local). En Docker, las vars vienen via env_file.
# read_env() no falla si el archivo no existe — es seguro llamarlo siempre.
environ.Env.read_env(BASE_DIR / ".env", raise_error=False)

# ── Seguridad ────────────────────────────────────────────────
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")

# ── Hosts permitidos ─────────────────────────────────────────
# Fallback permisivo para desarrollo; production.py overridea si es necesario
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

# ── Apps ─────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "daphne",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "ninja_extra",
    "ninja_jwt",
    "ninja_jwt.token_blacklist",
    "simple_history",
    "corsheaders",
    "django_q",
    "nested_admin",
]

LOCAL_APPS = [
    "core",
    "core_application",
    "modules.usuarios",
    "modules.tramites",
    "modules.asignaciones",
    "modules.consultas",
    "modules.notificaciones",
    "modules.conversaciones",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── Middleware ───────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "ninja.compatibility.files.fix_request_files_middleware",
    "core.middleware.static_cache.StaticDataCacheMiddleware",
  ]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ── Contraseñas ──────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Static& Media ───────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = BASE_DIR / "media"

# ── SAAA File Proxy URL ──────────────────────────────────────
# Base URL for SAAA file proxy endpoints.
# - Default: /api/archivo/public/  (relative, works with any host)
# - Override with absolute URL for production: FILE_PROXY_URL=http://localhost:12001/api/archivo/public/
FILE_PROXY_URL = env("FILE_PROXY_URL", default="/api/archivo/public/")

# ── SAAA Client Configuration ──────────────────────────────────
# SAAA microservicio de archivos — variables de entorno leídas del .env
# None de estos valores está hardcodeado en el código; todos usan env() con defaults.
SAAA_URL = env("SAAA_URL", default="http://172.16.93.83:9007/api/v1")
SAAA_APP_ID = env("SAAA_APP_ID", default="tramite-documentario")
SAAA_USUARIO_ID = env("SAAA_USUARIO_ID", default="1")
SAAA_TIPO_ARCHIVO_ID = env("SAAA_TIPO_ARCHIVO_ID", default="1")
SAAA_TIMEOUT = env("SAAA_TIMEOUT", default=30)

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": MEDIA_ROOT,
            "base_url": MEDIA_URL,
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ── Internacionalización ─────────────────────────────────────
LANGUAGE_CODE = "es"
TIME_ZONE = "America/Lima"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Auth ─────────────────────────────────────────────────────
AUTH_USER_MODEL = "usuarios.Usuario"

# ── Auth Storage Prefix ──────────────────────────────────────
# Single source of truth for cookie names. Cookie name = ${prefix}_access_token.
# Override with AUTH_STORAGE_PREFIX env var (must match NEXT_PUBLIC_AUTH_STORAGE_PREFIX
# on the frontend so cookies are read consistently on both sides).
AUTH_STORAGE_PREFIX = env("AUTH_STORAGE_PREFIX", default="tramite_documentario_auth")

# ── JWT (django-ninja-jwt) ───────────────────────────────────
NINJA_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    # Login propio en /api/auth/login/ — no usamos el built-in de ninja-jwt
    # WebSocket cookie name for JWTOKCookieMiddleware (reads access_token cookie)
    "WS_COOKIE_NAME": f"{AUTH_STORAGE_PREFIX}_access_token",
}

# ── Django Ninja Extra ───────────────────────────────────────
NINJA_EXTRA = {
    "INJECTOR_MODULES": [
        "modules.asignaciones.di.AsignacionesModule",
        "modules.tramites.di.TramitesModule",
        "modules.usuarios.di.UsuariosModule",
        "modules.consultas.di.ConsultasModule",
        "modules.notificaciones.di.NotificacionesModule",
        "modules.conversaciones.di.ConversacionesModule",
    ]
}

# ── Django Q2 (Workers) ──────────────────────────────────────
Q_CLUSTER = {
    "name": "generic-workers",
    "workers": 4,
    "recycle": 500,
    "timeout": 60,
    "queue_limit": 50,
    "bulk": 10,
    "orm": "default",
}

# ── Channels / ASGI ─────────────────────────────────────────
# ASGI application entry point — routed through ProtocolTypeRouter in config/asgi.py
ASGI_APPLICATION = "config.asgi.application"

# Redis URL for channel layer (channels_redis)
# Default: redis://localhost:6379/0 — override with REDIS_URL env var
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

# Channel layer configuration
# Uses Redis in production/development; InMemoryChannelLayer is forced in test settings
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("CHANNEL_LAYER_REDIS_URL", default=REDIS_URL)],
        },
    },
}

# ---------------------------------------------------------------------------
# Database — Override with USE_SQLITE=true for lightweight testing (e.g. Docker)
# ---------------------------------------------------------------------------
import os

if os.environ.get("USE_SQLITE", "").lower() in ("1", "true", "yes"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("SQLITE_PATH", ":memory:"),
        }
    }
else:
    # PostgreSQL — production.py debería overridear, pero dejamos helper limpio.
    # Lee DB_* con defaults razonables. Puerto interno estándar: 5432.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", default="cam_db"),
            "USER": env("DB_USER", default="cam_user"),
            "PASSWORD": env("DB_PASSWORD", default="changeme"),
            "HOST": env("DB_HOST", default="localhost"),
            "PORT": env("DB_PORT", default="5432"),
        }
    }
