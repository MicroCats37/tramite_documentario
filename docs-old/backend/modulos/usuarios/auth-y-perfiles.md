# Módulo Usuarios: Auth y Perfiles

## Visión General

El módulo `usuarios` centraliza todo lo relacionado a la identidad, autenticación y estructura organizacional del sistema. Se integra con `django.contrib.auth` y `rest_framework_simplejwt` para autenticación JWT.

---

## Modelos

### Permiso

```python
class Permiso(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.SlugField(unique=True, blank=True, max_length=255)
```

Modelo auxiliar que representa permisos individuales. Cada permiso tiene un nombre único y una descripción en formato slug. Este modelo existe como tabla de referencia para el sistema de permisos de Django, pero no se usa directamente en la aplicación — el sistema de grupos y permisos de Django gestiona la autorización a nivel de ViewSet mediante `DjangoModelPermissionsConMensaje`.

---

### Cargo

```python
class Cargo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    nivel = models.IntegerField(default=1, help_text="1: Operativo, 2: Supervisor, 3: Gerencia")
```

Representa los cargos o puestos dentro de la organización. El campo `nivel` sigue una escala jerárquica:

| Nivel | Nombre | Descripción |
|-------|--------|-------------|
| 1 | Operativo | Personal base, ejecución de tareas |
| 2 | Supervisor | Supervisión de equipo operativo |
| 3 | Gerencia | Dirección y toma de decisiones |

> **Nota**: El campo `cargo` fue **eliminado del token JWT** y de los filtros de búsqueda del `PerfilUsuarioViewSet`. La información de cargo ya no fluye en el login ni en el perfil del usuario. Esto indica que `Cargo` queda como modelo de referencia pero sin uso activo en el flujo de autenticación.

---

### Area

```python
class Area(SanitizeModelMixin, models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.SlugField(unique=True, blank=True, max_length=255)
    slug = models.SlugField(unique=True, blank=True, max_length=255)
```

Departamento o área dentro de la organización. Usa `SanitizeModelMixin` (ver sección Mixins) para normalizar strings vacíos a `NULL`.

**Auto-slug**: Al guardar, si `slug` está vacío, se genera automáticamente a partir de `nombre` usando `slugify`.

**Búsqueda**: Se busca por `slug` en los endpoints. El `AreaViewSet` expone filtros por `nombre` y búsqueda por `nombre` y `descripcion`.

---

### PerfilUsuario

```python
class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    cargo = models.ForeignKey(Cargo, on_delete=models.SET_NULL, null=True, blank=True)
    jefe = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="subordinados")
```

Perfil extendendido del usuario Django. Relación uno a uno con `User`.

**Relaciones:**
- `user` → `django.contrib.auth.User` (CASCADE)
- `area` → `Area` (SET_NULL si se elimina el área)
- `cargo` → `Cargo` (SET_NULL si se elimina el cargo)
- `jefe` → `self` (autoreferencia, un usuario puede tener un jefe)

**Validación**: `clean()` impide que un usuario sea su propio jefe.

**Uso en templates**: `f"{self.user.username} - ({self.area}) - {self.cargo}"`

---

## Autenticación JWT

### Login — `LoginView`

```python
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
```

Extiende `TokenObtainPairView` de `rest_framework_simplejwt`. El serializer personalizado **`LoginSerializer`** hace validaciones y añade claims al token:

**Validaciones en `get_token()`:**
1. Verifica que el usuario tenga `perfilusuario` → si no, lanza `ValidationError`
2. Verifica que el usuario tenga al menos un grupo/rol → si no, lanza `ValidationError`

**Claims inyectados en el Refresh Token:**

| Claim | Fuente |
|-------|--------|
| `user_id` | `user.id` |
| `username` | `user.username` |
| `fullname` | `user.first_name + user.last_name` |
| `email` | `user.email` |
| `rol` | `user.groups.first().name` |
| `area_slug` | `perfil.area.slug` (o `None`) |

**Validación en `validate()`**: Además de validar credenciales, retorna la información del usuario en la respuesta de login:

```python
data["user"] = {
    "user_id": user.id,
    "username": user.username,
    "fullname": f"{user.first_name} {user.last_name}".strip(),
    "email": user.email,
    "rol": rol.name,
    "area": area_data,
}
```

---

### Logout — `LogoutView`

```python
class LogoutView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        token = RefreshToken(request.data.get("refresh"))
        token.blacklist()
```

Implementa blacklist de refresh token. El endpoint espera el `refresh` token en el body y lo invalida.

> **Manejo de errores**: Si el token ya expiró o es inválido, igual retorna éxito (el usuario ya no puede usar ese token).

---

## Vistas

### MeView

```python
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(user)
        return Response(serializer.data)
```

Retorna el perfil completo del usuario autenticado. Serializado con `MeSerializer`.

---

### MisSolicitudesView

```python
class MisSolicitudesView(APIView):
    def get(self, request):
        qs_adjuntadas = Solicitud.objects.filter(
            usuario_solicitud_adjuntado__usuario=user,
            finalizado=False
        ).distinct()

        qs_asignadas = Solicitud.objects.filter(
            usuario_asignado=user,
            finalizado=False
        )
```

Retorna dos conjuntos de solicitudes pendientes:

1. **Solicitudes adjuntadas**: Aquellas donde el usuario está como `usuario_solicitud_adjuntado` y no están finalizadas.
2. **Solicitudes asignadas**: Aquellas donde el usuario es el `usuario_asignado` y no están finalizadas.

Ambas consultas comparten la condición `finalizado=False`.

---

## Serializers Clave

### MeSerializer

```python
class MeSerializer(serializers.ModelSerializer):
    fullname = serializers.SerializerMethodField()
    rol = serializers.SerializerMethodField()
    perfil = serializers.SerializerMethodField()
    permisos = serializers.SerializerMethodField()
```

Expone:
- `id`, `username`, `email`
- `fullname`: concatenación de first_name + last_name
- `rol`: nombre del primer grupo del usuario
- `perfil`: `{ id, area }` del `PerfilUsuario`
- `permisos`: lista de todos los permisos efectivos del usuario

---

## Permisos

### DjangoModelPermissionsConMensaje

```python
from .permissions.django_permissions_coment import DjangoModelPermissionsConMensaje
```

Permission class personalizada usada en `PerfilUsuarioViewSet`. Ver documento de permisos para detalle completo.

---

## Rutas (`urls.py`)

```
login/          → LoginView (POST)
logout/         → LogoutView (POST)
me/             → MeView (GET)
pendientes/     → MisSolicitudesView (GET)
perfil-usuario/ → PerfilUsuarioViewSet (CRUD, solo lectura)
areas/          → AreaViewSet (CRUD, solo lectura)
```

El router expone los ViewSets con las acciones estándar de DRF (`list`, `retrieve`, etc.).

---

## Dependencias de Otras Apps

El módulo `usuarios` es **consumido por**:

- **`solicitudes`**: `MisSolicitudesView` filtra por `Solicitud` (relación `usuario_asignado`, `usuario_solicitud_adjuntado`).
- **`expedientes`**: `ResumenExpedienteSerializer` se usa en `MisSolicitudesView` para serializar las solicitudes.
- **`common/utils/mixins`**: Los mixins de sanitización son aplicados a los modelos y serializers de `usuarios` (`Area` usa `SanitizeModelMixin`, `AreaSerializer` usa `SanitizeEmptyStringMixin`).

---

## Modelo de Datos (Relaciones)

```
User (django.contrib.auth)
  └─ PerfilUsuario (OneToOne)
       ├─ Area (FK, SET_NULL)
       ├─ Cargo (FK, SET_NULL) ← sin uso activo en auth
       └─ PerfilUsuario (FK self, SET_NULL, related_name="subordinados")
```
