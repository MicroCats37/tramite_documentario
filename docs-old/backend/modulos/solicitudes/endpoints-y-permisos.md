# ViewSets, Endpoints y Sistema de Permisos en Cascada

## 1. Arquitectura General

El módulo expone dos ViewSets REST mediante Django REST Framework:

| ViewSet | Router | Base URL | Propósito |
|---------|--------|----------|-----------|
| `SolicitudViewSet` | `DefaultRouter` | `/api/solicitudes/` | CRUD de solicitudes + acciones de bandeja |
| `ComentarioSolicitudViewSet` | `DefaultRouter` | `/api/comentarios-solicitud/` | Crear y leer comentarios |

Ambos routers se registran en `solicitudes/urls.py`:

```python
router.register(r"solicitudes", SolicitudViewSet, basename="solicitudes")
router.register(r"comentarios-solicitud", ComentarioSolicitudViewSet, basename="comentarios-solicitud")
```

---

## 2. Endpoints del ViewSet `SolicitudViewSet`

### 2.1 Endpoints Estándar DRF

| Método | URL | Acción | Descripción |
|--------|-----|--------|-------------|
| `GET` | `/api/solicitudes/` | `list` | Lista solicitudes (filtrable, paginable) |
| `POST` | `/api/solicitudes/` | `create` | Crear nueva solicitud |
| `GET` | `/api/solicitudes/<pk>/` | `retrieve` | Detalle de una solicitud |
| `PUT` | `/api/solicitudes/<pk>/` | `update` | Reemplazo completo |
| `PATCH` | `/api/solicitudes/<pk>/` | `partial_update` | Actualización parcial |
| `DELETE` | `/api/solicitudes/<pk>/` | `destroy` | **Bloqueado para todos** (siempre retorna 403) |

### 2.2 Endpoints de Bandeja (Custom Actions)

| Método | URL | Acción | Descripción |
|--------|-----|--------|-------------|
| `GET` | `/api/solicitudes/asignadas/` | `asignadas` | Solicitudes donde `usuario_asignado = request.user` |
| `GET` | `/api/solicitudes/creadas/` | `creadas` | Solicitudes cuyo `expediente.creado_por = request.user` |
| `GET` | `/api/solicitudes/mi-area/` | `mi_area` | Solicitudes del área del usuario (`perfil.area`) |
| `GET` | `/api/solicitudes/adjuntadas/` | `adjuntadas` | Solicitudes donde el usuario está en `usuarios_adjuntados` |

### 2.3 Filtros Soportados

| Parámetro | Ejemplo | Descripción |
|-----------|---------|-------------|
| `estado` | `?estado=EN_GESTION_MP` | Filtrar por estado |
| `finalizado` | `?finalizado=false` | Filtrar por estado de cierre |
| `view` | `?view=card` | Devuelve `SolicitudCardQuerySerializer` (con expediente anidado) |
| `search` | `?search=LIMA-2026` | Búsqueda por `id_publico` |

### 2.4 Selección Dinámica de Serializer

```python
def get_serializer_class(self):
    if self.request.query_params.get("view") == "card":
        return SolicitudCardQuerySerializer           # Incluye expediente anidado completo
    if self.action in ["list", "retrieve", "asignadas", "creadas", "mi_area", "adjuntadas"]:
        return SolicitudQuerySerializer               # lectura ligera sin expediente
    return SolicitudMutationSerializer                # create/update con lógica transaccional
```

---

## 3. Endpoints del ViewSet `ComentarioSolicitudViewSet`

| Método | URL | Acción | Descripción |
|--------|-----|--------|-------------|
| `GET` | `/api/comentarios-solicitud/` | `list` | Lista comentarios (filtro por `solicitud_id`) |
| `POST` | `/api/comentarios-solicitud/` | `create` | Crear comentario |
| `GET` | `/api/comentarios-solicitud/<pk>/` | `retrieve` | Detalle de comentario |
| `PUT/PATCH/DELETE` | `/api/comentarios-solicitud/<pk>/` | `update/partial_update/destroy` | **Bloqueados** |

### Filtro por Solicitud

```python
# ComentarioSolicitudViewSet.list()
solicitud_id = request.query_params.get("solicitud_id")
if solicitud_id:
    qs = ComentarioSolicitud.objects.filter(solicitud_id=solicitud_id)
```

---

## 4. Sistema de Permisos en Cascada

### 4.1 Cadena de Verificación (Para Solicitudes)

```
Request llega
    │
    ▼
┌─────────────────────────────┐
│ 1. IsAuthenticated          │ ── 401 si no autenticado
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ 2. DjangoModelPermissions   │ ── 403 si no tiene permiso Django (add/change/view)
│    (DjangoModelPermissions  │
│     ConMensaje)             │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ 3. Permiso por Rol          │ ── 403 si el rol no tiene acceso a la acción
│    (cascada según grupo)    │
└──────────────┬──────────────┘
               ▼
         ¿Tiene objeto?
          /          \
        Sí           No (create)
         │             │
         ▼             ▼
┌─────────────────┐  ┌─────────────────────────────┐
│ has_object_     │  │ has_permission (create)     │
│ permission      │  │ (verifica expediente,       │
│ (valida estado, │  │  estado, no auto-asignación)│
│  campos, rol)   │  └─────────────────────────────┘
└─────────────────┘
```

### 4.2 Permisos por Rol — `SolicitudViewSet`

#### Recepción Mesa de Partes

```python
# RecepcionMesaDePartesSolicitudPermission
CAMPOS_PERMITIDOS = {"estado", "usuario_asignado", "usuarios_adjuntados", "area_responsable"}

# CREATE
- expediente es obligatorio
- estado debe estar en MESA_DE_PARTES_EDITABLES
- finalizado no puede ser True
- no puede asignarse a sí mismo
- no puede asignar a alguien de su misma área

# UPDATE/PATCH
- solo puede editar si el usuario creó el expediente asociado
- estado actual debe estar en MESA_DE_PARTES_EDITABLES
- no puede usar estados fuera de MESA_DE_PARTES
- no puede marcar finalizado
- campos enviados deben estar en CAMPOS_PERMITIDOS

# DESTROY → siempre False
```

#### Supervisor Mesa de Partes

```python
# SupervisorMesaDePartesSolicitudPermission
CAMPOS_PERMITIDOS = {"estado", "usuario_asignado", "usuarios_adjuntados"}

# CREATE → False (supervisores no crean solicitudes)

# UPDATE/PATCH
- estado actual debe estar en SUPERVISOR_EDITABLES
- nuevo estado debe estar en SUPERVISOR (no puede asignar a área)
- no puede marcar finalizado
- campos enviados deben estar en CAMPOS_PERMITIDOS

# DESTROY → siempre False
```

#### Encargado de Área

```python
# EncargadoAreaSolicitudPermission
CAMPOS_PERMITIDOS = {"estado", "usuario_asignado", "finalizado", "usuarios_adjuntados", "anexos"}

# CREATE → False

# UPDATE/PATCH
- usuario_asignado debe ser el usuario actual
- estado actual debe estar en AREA_ENCARGADA_EDITABLES
- nuevo estado debe estar en AREA_ENCARGADA
- SOLO puede marcar finalizado=True cuando nuevo_estado == "CERRADO"
- campos enviados deben estar en CAMPOS_PERMITIDOS

# DESTROY → siempre False
```

#### Creador de Flujos

```python
# get_permissions()
if user.groups.filter(name="Creador de Flujos").exists():
    return base_permissions  # Solo IsAuthenticated + DjangoModelPermissions, sin restricción de rol
```

> **Creador de Flujos** tiene acceso completo al ViewSet sin restricciones de estado ni de campos. Esto es intencional: son los administradores del sistema de flujo.

### 4.3 Permisos por Rol — `ComentarioSolicitudViewSet`

```python
permission_classes = [IsAuthenticated, ComentarioSolicitudPermission]
```

#### Reglas de `ComentarioSolicitudPermission`

| Acción | Regla |
|--------|-------|
| `list` / `retrieve` | Cualquier usuario autenticado |
| `create` | Validado en `check_create()` |
| `update` / `partial_update` / `destroy` | **Siempre False** (comentarios inmutables) |

#### Lógica de `check_create()`

```python
def check_create(self, request):
    user = request.user

    # Superuser o Creador de Flujos → siempre puede comentar
    if user.is_superuser or user.groups.filter(name="Creador de Flujos").exists():
        return True

    # Extraer solicitud_id (blindado contra middleware que consumió el stream)
    # ... fallback a request.data.get('data') con JSON parse ...

    # Solicitud no debe estar finalizada (excepto Creador de Flujos)
    if solicitud.finalizado:
        raise PermissionDenied("No puedes comentar en una solicitud finalizada.")

    # Usuario debe cumplir AL MENOS UNA de:
    # 1. Es el creador del expediente asociado
    # 2. Es el usuario_asignado de la solicitud
    # 3. Está en usuarios_adjuntados
    # 4. Es Supervisor de Mesa de Partes
```

---

## 5. Campos Protegidos por Rol

| Campo | Recepción MP | Supervisor MP | Encargado Área | Creador Flujos |
|-------|:------------:|:-------------:|:--------------:|:--------------:|
| `estado` | ✅ | ✅ | ✅ | ✅ |
| `usuario_asignado` | ✅ | ✅ | ✅ | ✅ |
| `area_responsable` | ✅ | ❌ | ❌ | ✅ |
| `usuarios_adjuntados` | ✅ | ✅ | ✅ | ✅ |
| `finalizado` | ❌ | ❌ | ✅ (solo en CERRADO) | ✅ |
| `anexos` | ❌ | ❌ | ✅ | ✅ |
| `prioridad` | ❌ | ❌ | ❌ | ✅ |

---

## 6. Transaccionalidad

### Creación de Solicitud (Atomic)

```python
# SolicitudMutationSerializer.create()
with transaction.atomic():
    # A. Crear Solicitud
    solicitud = super().create(validated_data)
    # B. Procesar M2M usuarios_adjuntados (add/remove granular)
    self.process_m2m_diff(...)
    # C. Procesar anexos (archivos + registros en SolicitudArchivoAnexo)
    self.procesar_anexos(solicitud, items_anexos)
```

### Actualización de Solicitud (Atomic)

```python
# SolicitudMutationSerializer.update()
with transaction.atomic():
    # Procesar estado de cierre (inyecta fecha_cierre si finalize=True)
    if finalizado_flag is not None:
        instance = SolicitudService.procesar_estado_final(instance, finalizado_flag)
    instance = super().update(instance, validated_data)
    self.process_m2m_diff(...)
    self.procesar_anexos(instance, items_anexos)
```

### Creación de Comentario (Atomic)

```python
# ComentarioSolicitudMutationSerializer.create()
with transaction.atomic():
    comentario = super().create(validated_data)
    self.procesar_anexos(comentario, items_anexos)
```

---

## 7. SafeFieldCheckMixin

Todas las clases de permiso heredan de `SafeFieldCheckMixin` que proporciona:

```python
def validate_allowed_fields(self, request, allowed_fields: set):
    """Lanza PermissionDenied si request contiene campos fuera de allowed_fields."""
    forbidden = set(request.data.keys()) - allowed_fields
    if forbidden:
        raise PermissionDenied(
            f"Campos no permitidos para esta acción: {forbidden}"
        )
```

Esto garantiza que aunque el frontend envíe campos adicionales (como `creado_por` o `modificado_por`), estos son **rechazados en la capa de permisos** antes de llegar al serializer.
