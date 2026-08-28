# Visión Global del Backend — Arquitectura General

> **Aplicación**: Mesa de Partes CIP
> **Stack**: Django 4.x + Django REST Framework + PostgreSQL
> **Versión del documento**: 1.0
> **Última actualización**: Agosto 2026

---

## 1. Stack Tecnológico

### 1.1 Django 4.x (Framework Web)

Django es el framework principal que proporciona:

- **ORM** — Mapeo objeto-relacional para todas las operaciones de base de datos
- **Admin** — Interfaz administrativa automática (`/admin/`)
- **Auth** — Sistema de autenticación integrado con User model
- **Sessions** — Middleware de sesiones para autenticación session-based
- **Messages** — Framework de mensajes flash entre vistas
- **Static/Media** — Gestión de archivos estáticos y multimedia

### 1.2 Django REST Framework (DRF)

DRF se superpone a Django para exponer una **API REST** consumida por el frontend:

```
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 10,
}
```

**Componentes clave usados:**
- `DefaultRouter` — Auto-genera rutas CRUD estándar para ViewSets
- `ViewSet` — Vistas RESTful pre-construidas (list, create, retrieve, update, destroy)
- `Serializer` — Validación y transformación de datos JSON <-> Model
- `Authentication` / `Permission` — Filtros por rol en cada request

### 1.3 JWT (JSON Web Tokens)

El sistema usa **SimpleJWT** (`rest_framework_simplejwt`) para autenticación stateless:

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=360),  # 6 horas
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),       # 1 día
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "TOKEN_OBTAIN_SERIALIZER": "usuarios.serializers.LoginSerializer"
}
```

**Flujo de autenticación:**

```
1. POST /api/token/   → {username, password}
   Response: {access: "<jwt>", refresh: "<jwt>"}

2. POST /api/token/refresh/  → {refresh: "<jwt>"}
   Response: {access: "<new_jwt>"}

3. Todas las requests posteriores:
   Headers: Authorization: Bearer <access_token>
```

**Endpoints JWT:**
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/token/` | Login — obtiene access + refresh tokens |
| POST | `/api/token/refresh/` | Refresca el access token |

### 1.4 UUIDs como Primary Keys

Todas las tablas principales usan **UUID** en lugar de auto-increment integer:

```python
# Ejemplo: Solicitud
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

# Ejemplo: Expediente
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
```

**Ventajas:**
- **Seguridad**: No se puede adivinar el ID de un recurso (`/api/solicitudes/3` vs `/api/solicitudes/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11`)
- **URLs públicas seguras**: Los IDs públicos (`LIMA-2026-0001`) se generan separadamente y son lo que ve el usuario
- **No hay enumeración**: Un atacante no puede hacer scraping de todos los registros

**Tablas con UUID como PK:**
- `usuarios.Permiso` (int, legacy)
- `usuarios.Cargo` (int, legacy)
- `usuarios.Area` (int, legacy)
- `usuarios.PerfilUsuario` (int, legacy)
- `solicitudes.Solicitud` ✅ UUID
- `solicitudes.SolicitudArchivoAnexo` ✅ UUID
- `solicitudes.ComentarioSolicitud` ✅ UUID
- `solicitaciones.ComentarioSolicitudArchivoAnexo` ✅ UUID
- `solicitudes.UsuarioSolicitudAdjuntado` ✅ UUID
- `expedientes.Expediente` ✅ UUID
- `expedientes.ExpedienteArchivoAnexo` ✅ UUID

### 1.5 SimpleHistory (Auditoría)

`simple_history` crea **tablas影子 (shadow)** que rastrean cada cambio en los modelos:

```python
# En el modelo:
history = HistoricalRecords()

# Django crea automáticamente:
# - historical_solicitud
# - historical_comentario_solicitud
# - historical_expediente
```

**Características:**
- Cada `save()` registra: qué cambió, cuándo, y **quién lo hizo** (vía `HistoricalRecords` middleware)
- Los registros históricos NO se pueden modificar ni eliminar (inmutables)
- Se consultan desde el admin o vía API para auditorías

**Middleware que habilita el tracking de usuario:**

```python
MIDDLEWARE = [
    # ...
    'simple_history.middleware.HistoryRequestMiddleware',  # Registra request.user en cada save
]
```

---

## 2. Apps y sus Responsabilidades

### 2.1 Diagrama de Apps

```
┌─────────────────────────────────────────────────────────────┐
│                      Django Project                          │
│                                                              │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ usuarios │  │ solicitudes  │  │     expedientes        │  │
│  │          │  │              │  │                       │  │
│  │ • Users  │  │ • Solicitud  │  │ • Expediente          │  │
│  │ • Areas  │  │ • Comentario │  │ • ArchivoAnexo        │  │
│  │ • Cargos │  │ • Anexos     │  │ • Antecedentes M2M    │  │
│  │ • Perfil │  │ • Adjuntos   │  │                       │  │
│  └──────────┘  └──────────────┘  └───────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   common (shared)                     │   │
│  │  • Constants (estados, choices)                       │   │
│  │  • Mixins (SanitizeModelMixin)                        │   │
│  │  • Utils                                             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 App `usuarios`

**Responsabilidad**: Gestión de usuarios, perfiles, organigrama.

**Modelos:**
| Modelo | PK | Descripción |
|--------|----|-------------|
| `Permiso` | int | Permisos individuales (legacy, no usado activamente) |
| `Cargo` | int | Roles operativos: Recepcionista, Supervisor, Encargado de Área |
| `Area` | int | Áreas organizacionales: Mesa de Partes, Logística, etc. |
| `PerfilUsuario` | int | Perfil extendido del User de Django: área, cargo, jefe |

**PerfilUsuario** es el modelo central del organigrama:

```python
class PerfilUsuario(models.Model):
    user   = models.OneToOneField(User)       # Usuario Django
    area   = models.ForeignKey(Area, null=True)
    cargo  = models.ForeignKey(Cargo, null=True)
    jefe   = models.ForeignKey("self", null=True)  # Autorreferencia para organigrama
```

**Vistas REST:**
- `LoginView` — `/api/login/` (POST)
- `LogoutView` — `/api/logout/` (POST)
- `MeView` — `/api/me/` (GET, retorna perfil del usuario autenticado)
- `PerfilUsuarioViewSet` — `/api/perfil-usuario/` (CRUD completo)
- `AreaViewSet` — `/api/areas/` (CRUD completo)
- `MisSolicitudesView` — `/api/pendientes/` (GET, solicitudes donde el usuario está involucrado)

### 2.3 App `solicitudes`

**Responsabilidad**: Flujo de solicitudes, comentarios, archivos adjuntos y transiciones de estado.

**Modelos:**
| Modelo | PK | Notas |
|--------|----|-------|
| `Solicitud` | UUID | Principal — enlazada 1:1 con Expediente |
| `SolicitudArchivoAnexo` | UUID | Archivos de la solicitud padre |
| `ComentarioSolicitud` | UUID | Con soporte para hilos (parent_id) |
| `ComentarioSolicitudArchivoAnexo` | UUID | Archivos de cada comentario |
| `UsuarioSolicitudAdjuntado` | UUID | Tabla intermedia M2M para colaboradores |

**Relación Expediente ↔ Solicitud:**

```
Expediente ──1:1── Solicitud
     │                │
     └── id_publico ←─┘  (LIMA-2026-0001)
     └── Se crea primero
     └── Es PROTEGIDO (no se elimina si tiene solicitud)
```

**Vistas REST:**
- `SolicitudViewSet` — `/api/solicitudes/` (CRUD completo)
- `ComentarioSolicitudViewSet` — `/api/comentarios-solicitud/` (CRUD completo)

### 2.4 App `expedientes`

**Responsabilidad**: Expedientes digitales con archivos y metadatos.

**Modelos:**
| Modelo | PK | Notas |
|--------|----|-------|
| `Expediente` | UUID | Datos del trámite + archivo principal |
| `ExpedienteArchivoAnexo` | UUID | Archivos adicionales |

**Relación M2M de Antecedentes:**

```python
class Expediente(models.Model):
    antecedentes = models.ManyToManyField(
        'self',               # Auto-referencia
        symmetrical=False,    # No es simétrica (A ссылается на B ≠ B ссылается на A)
        blank=True
    )
```

**Vistas REST:**
- `ExpedienteViewSet` — `/api/expedientes/` (CRUD completo)

---

## 3. Sistema de Permisos (RBAC)

### 3.1 Grupos Globales (Django Groups)

El sistema define **4 grupos a nivel de sistema** que.controlan el acceso:

| Grupo | Descripción |
|-------|-------------|
| `Mesa de Partes` | Recepción — crea solicitudes, asigna áreas |
| `Supervisor` | Supervisión — supervisa toda la bandeja, reassigna |
| `Area Encargada` | Gestión — procesa solicitudes de su área |
| `Administrador` | Superusuario — acceso total al admin de Django |

### 3.2 Permisos a Nivel de Campo (Field-Level)

No solo se restringe *qué* puede hacer un usuario, sino *qué campos* puede modificar:

**Mesa de Partes:**
```python
CAMPOS_PERMITIDOS = {"estado", "usuario_asignado", "usuarios_adjuntados", "area_responsable"}
```

**Supervisor:**
```python
CAMPOS_PERMITIDOS = {"estado", "usuario_asignado", "usuarios_adjuntados"}
```

**Área Encargada:**
```python
CAMPOS_PERMITIDOS = {"estado", "usuario_asignado", "finalizado", "usuarios_adjuntados", "anexos"}
```

### 3.3 Validación de Estados por Rol

Cada estado tiene una lista de `editable_by` que indica qué roles pueden modificarlo:

| Estado | Mesa de Partes | Supervisor | Área Encargada |
|--------|:--------------:|:----------:|:--------------:|
| `EN_GESTION_MP` | ✅ editable | ✅ editable | ❌ |
| `REENVIO_MP` | ✅ editable | ❌ | ❌ |
| `ENVIADO_A_AREA` | ✅ editable | ✅ editable | ✅ editable |
| `EN_TRAMITE_AREA` | ❌ | ❌ | ✅ editable |
| `CERRADO` | ❌ | ❌ | ✅ editable (solo `finalizado=True`) |

---

## 4. Rutas API Principales

### 4.1 URLs Raíz

```
/api/
├── login/                  → LoginView (POST)
/api/token/                → TokenObtainPairView (POST)
/api/token/refresh/        → TokenRefreshView (POST)
/api/me/                   → MeView (GET)
/api/logout/               → LogoutView (POST)
/api/pendientes/           → MisSolicitudesView (GET)

├── usuarios/
│   ├── perfil-usuario/    → PerfilUsuarioViewSet
│   └── areas/             → AreaViewSet

├── solicitudes/
│   ├── solicitudes/       → SolicitudViewSet
│   └── comentarios-solicitud/ → ComentarioSolicitudViewSet

├── expedientes/
│   └── expedientes/        → ExpedienteViewSet
```

### 4.2 Rutas protegidas

Todas las rutas bajo `/api/` requieren `Authorization: Bearer <token>` excepto `/api/token/` y `/api/login/`.

---

## 5. Seguridad y Validación

### 5.1 Sanitización de Inputs

Todos los modelos heredan de `SanitizeModelMixin` que limpia datos antes de persistir:

```python
class Solicitud(SanitizeModelMixin, models.Model):
    # Aplica sanitización automática a todos los campos de texto
```

### 5.2 Renombrado de Archivos Subidos

Los archivos se renombran con UUID para evitar:
- Enumeración de archivos (`archivo_1.pdf`, `archivo_2.pdf`)
- Colisiones de nombre
- Inyección de paths maliciosos

```python
def ruta_anexo_solicitud(instance, filename):
    ext = filename.split('.')[-1]
    filename_seguro = f"{uuid.uuid4()}.{ext}"
    return os.path.join(f"solicitudes/{instance.solicitud.id_publico}/anexos/", filename_seguro)
```

### 5.3 Validación de Relaciones (on_delete)

| Relación | on_delete | Razón |
|----------|-----------|-------|
| PerfilUsuario → User | `CASCADE` | Si se elimina el usuario, se elimina su perfil |
| Solicitud → Expediente | `PROTECT` | No elimina expediente si tiene solicitudes |
| Solicitud → Usuario Asignado | `PROTECT` | Mantiene trazabilidad |
| Expediente → User (creado_por) | `PROTECT` | No elimina usuarios con expedientes creados |

---

## 6. Middleware Stack

```
Request Flow:

1. corsheaders.middleware.CorsMiddleware         → CORS headers
2. silk.middleware.SilkyMiddleware               → Profiling (dev)
3. django.middleware.common.CommonMiddleware     → URL normalization
4. django.middleware.security.SecurityMiddleware → Security headers
5. whitenoise.middleware.WhiteNoiseMiddleware   → Static files
6. django.contrib.sessions.middleware.SessionMiddleware → Sessions
7. django.middleware.csrf.CsrfViewMiddleware    → CSRF protection
8. django.contrib.auth.middleware.AuthenticationMiddleware → Auth
9. django.contrib.messages.middleware.MessageMiddleware → Flash messages
10. django.middleware.clickjacking.XFrameOptionsMiddleware → Clickjacking protection
11. simple_history.middleware.HistoryRequestMiddleware → Audit user tracking
```

---

## 7. Dependencias Clave (INSTALLED_APPS)

```python
INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps del proyecto
    'usuarios',
    'expedientes',
    'solicitudes',

    # REST API
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',

    # Utilities
    'corsheaders',          # Cross-Origin
    'django_filters',       # Filtering
    'nested_admin',         # Nested admin (para comentarios/anexos)
    'simple_history',       # Auditoría
    'silk',                 # Profiling/debug de API
    'whitenoise',           # Static files en producción
]
```

---

## 8. Configuración por Entorno

```python
MODE = os.getenv('MODE', 'development')

if MODE == 'production':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': DB_NAME,
            'USER': DB_USER,
            'PASSWORD': DB_PASSWORD,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

**Entornos:**
- `development`: SQLite local
- `production`: PostgreSQL via variables `DB_*`

---

## 9. Timezone y Localización

```python
TIME_ZONE = 'America/Lima'   # Zona horaria de Perú
LANGUAGE_CODE = 'es-pe'      # Español peruano
USE_I18N = True              # Internacionalización activa
USE_TZ = True                # Timestamps con timezoneaware
```

Todos los timestamps se almacenan en UTC y se muestran en hora local (Lima).
