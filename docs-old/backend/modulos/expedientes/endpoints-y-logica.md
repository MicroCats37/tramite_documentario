# Módulo Expedientes — Endpoints y Lógica de Negocio

## Índice

1. [Visión General](#visión-general)
2. [Router y URLs](#router-y-urls)
3. [Patrón Query/Mutation Serializer](#patrón-querymutation-serializer)
4. [ViewSets](#viewsets)
5. [Reglas de Negocio (ExpedienteService)](#reglas-de-negocio-expedienteservice)
6. [Carga de Archivos](#carga-de-archivos)
7. [Sistema de Permisos](#sistema-de-permisos)
8. [Mixins Compartidos](#mixins-compartidos)
9. [Transacciones Atómicas](#transacciones-atómicas)
10. [Acciones Personalizadas (Actions)](#acciones-personalizadas-actions)
11. [Filtrado y Búsqueda](#filtrado-y-búsqueda)

---

## Visión General

**Aplicación:** `backend/expedientes/`
**Serializers:** 4 (ExpedienteQuerySerializer, ExpedienteMutationSerializer, ExpedienteArchivoAnexoSerializer, SolicitudMiniSerializer)
**ViewSets:** 2 (ExpedienteViewSet, ExpedienteArchivoAnexoViewSet)
**Service:** ExpedienteService

---

## Router y URLs

**Archivo:** `backend/expedientes/urls.py`

```python
router = DefaultRouter()
router.register(r"expedientes", ExpedienteViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
```

**URLs generadas:**

| Método | Endpoint | Action | Descripción |
|--------|----------|--------|-------------|
| `GET` | `/api/expedientes/` | `list` | Lista expedientes (filtrado por usuario) |
| `POST` | `/api/expedientes/` | `create` | Crea expediente con anexos |
| `GET` | `/api/expedientes/{uuid}/` | `retrieve` | Detalle de expediente |
| `PUT/PATCH` | `/api/expedientes/{uuid}/` | `update/partial_update` | Actualiza expediente |
| `DELETE` | `/api/expedientes/{uuid}/` | `destroy` | Elimina expediente |
| `GET` | `/api/expedientes/creadas/` | `creadas` | Expedientes creados por el usuario actual |
| `GET` | `/api/expedientes/creadas-sin-solicitud/` | `creadas_sin_solicitud` | Expedientes sin solicitud asociada |

---

## Patrón Query/Mutation Serializer

El módulo Expedientes implementa el patrón **Query/Mutation** recomendado en el proyecto:

### ExpedienteQuerySerializer (Lectura)

**Herencia:** `serializers.ModelSerializer` directo.

**Uso:** `list`, `retrieve`, y acciones `creadas`, `creadas_sin_solicitud`.

**Campos incluidos:**
- `id` (UUID interno)
- `id_publico` (código visible LIMA-YYYYMMDD-XXXX)
- Todos los campos de persona (dni, ruc, cip, razon_social, apellidos, nombres, telefono, correo)
- `tipo_documento`, `numero_documento`, `numero_folios`, `asunto`
- `archivo_principal` (URL al archivo)
- `anexos` → nested `ExpedienteArchivoAnexoSerializer` (muchos)
- `solicitud` → nested `SolicitudQuerySerializer` (relación opcional)
- `creado_por` → nested `UsuarioSerializer`
- `modificado_por` → nested `UsuarioSerializer`
- `observaciones`
- `fecha_creacion`, `fecha_actualizacion`
- `antecedentes` (M2M con autofetch)

**Todos los campos son `read_only=True`** (no se puede escribir con este serializer).

### ExpedienteMutationSerializer (Escritura)

**Herencia en orden:**
```python
class ExpedienteMutationSerializer(
    SanitizeEmptyStringMixin,  # 1°: sanitiza strings vacíos → null
    JsonPayloadMixin,          # 2°: manejo de payload JSON
    AnexosMixin,               # 3°: procesamiento de anexos
    RelationshipDiffMixin,     # 4°: manejo de M2M delta
    serializers.ModelSerializer
):
```

**Mixins en detalle:**

| Mixin | Responsabilidad |
|-------|----------------|
| `SanitizeEmptyStringMixin` | Convierte strings vacíos (`""`) a `null` antes de validación. |
| `JsonPayloadMixin` | Permite recibir datos como JSON en el body. |
| `AnexosMixin` | Procesa la lista de anexos en `create`/`update`: crea/asocia archivos a `ExpedienteArchivoAnexo`. Configuración: `child_model = ExpedienteArchivoAnexo`, `fk_field = 'expediente'`. |
| `RelationshipDiffMixin` | Maneja el patrón delta para M2M: `{ add: [...], remove: [...] }`. Usa `process_m2m_diff()` para aplicar cambios en transacciones. |

**Campos de entrada (write_only):**
- `anexos`: `ListField(DictField())` — lista de objetos con datos de anexos (JSON limpio, no archivos multipart).
- `antecedentes`: `DictField()` — modo delta `{ add: [uuids], remove: [uuids] }`.
- `solicitud`: `SolicitudMiniSerializer` (solo lectura — no se puede asignar directamente).

**Flujo en `create`:**
1. `validate()` → llama a `ExpedienteService.validar_datos()`
2. Extrae `anexos` y `antecedentes` del payload
3. Asigna `creado_por = request.user`
4. Genera `id_publico` si no existe (vía `ExpedienteService.generar_id_publico()`)
5. `super().create()` → crea el Expediente
6. `self.procesar_anexos()` → crea registros `ExpedienteArchivoAnexo`
7. `self.process_m2m_diff()` → agrega antecedentes

**Flujo en `update`:**
1. `validate()` → re-valida reglas de negocio
2. Asigna `modificado_por = request.user`
3. `super().update()` → actualiza el Expediente
4. `self.procesar_anexos()` → procesa anexos (crea nuevos, depende del mixin)
5. `self.process_m2m_diff()` → aplica delta de antecedentes (add + remove)

**`to_representation()`:** Delega completamente a `ExpedienteQuerySerializer` para formatear la respuesta.

### ExpedienteArchivoAnexoSerializer

**Uso:** CRUD individual de anexos + lectura anidada en `ExpedienteQuerySerializer`.

**Campos:** `id`, `archivo_anexo`, `descripcion`, `fecha_creacion` (solo lectura).

---

## ViewSets

### ExpedienteViewSet

**Clase:** `viewsets.ModelViewSet`
**QuerySet base:**
```python
queryset = Expediente.objects.select_related(
    'creado_por', 'modificado_por', 'solicitud'
).all().order_by("-fecha_creacion")
```

**Selección de Serializer:**
```python
def get_serializer_class(self):
    acciones_lectura = ["list", "retrieve", "creadas", "creadas_sin_solicitud"]
    if self.action in acciones_lectura:
        return ExpedienteQuerySerializer
    return ExpedienteMutationSerializer
```

**Parser:** Heredado del setting global (`NestedMultiPartParser` configurado globalmente para manejar archivos + JSON en la misma request).

#### Permisos Dinámicos

```python
def get_permissions(self):
    base_permissions = [permissions.IsAuthenticated(), DjangoModelPermissionsConMensaje()]
    
    if user.groups.filter(name="Recepcion Mesa de Partes").exists():
        return base_permissions + [MesaDePartesExpedientePermission()]
    
    if user.groups.filter(name="Supervisor Mesa de Partes").exists():
        return base_permissions + [MesaDePartesExpedientePermission()]
    
    if user.groups.filter(name="Creador de Flujos").exists():
        return base_permissions  # Sin permiso específico
    
    return base_permissions
```

**Grupos y permisos asociados:**

| Grupo | Permiso Adicional |
|-------|-------------------|
| Recepción Mesa de Partes | `MesaDePartesExpedientePermission` |
| Supervisor Mesa de Partes | `MesaDePartesExpedientePermission` |
| Creador de Flujos | Sin permiso adicional (solo base) |
| (default) | Solo permisos base |

### ExpedienteArchivoAnexoViewSet

**Clase:** `viewsets.ModelViewSet`
**QuerySet base:** `ExpedienteArchivoAnexo.objects.all()`

**Filtrado por creador:**
```python
def get_queryset(self):
    user = self.request.user
    return super().get_queryset().filter(expediente__creado_por=user)
```

**Nota:** Solo muestra anexos de expedientes creados por el usuario actual (filtro de seguridad a nivel de query).

#### Permisos Dinámicos

```python
def get_permissions(self):
    base_permissions = [IsAuthenticated(), DjangoModelPermissionsConMensaje()]
    
    if user.groups.filter(name="Recepcion Mesa de Partes").exists():
        return base_permissions + [RecepcionMesaDePartesExpedienteArchivoAnexoPermission()]
    
    if user.groups.filter(name="Supervisor Mesa de Partes").exists():
        return base_permissions + [SupervisorMesaDePartesExpedienteArchivoAnexoPermission()]
    
    if user.groups.filter(name="Encargado de Área").exists():
        return base_permissions + [EncargadoAreaExpedienteArchivoAnexoPermission()]
    
    if user.groups.filter(name="Creador de Flujos").exists():
        return base_permissions
    
    return base_permissions
```

| Grupo | Permiso Adicional |
|-------|-------------------|
| Recepción Mesa de Partes | `RecepcionMesaDePartesExpedienteArchivoAnexoPermission` |
| Supervisor Mesa de Partes | `SupervisorMesaDePartesExpedienteArchivoAnexoPermission` |
| Encargado de Área | `EncargadoAreaExpedienteArchivoAnexoPermission` |
| Creador de Flujos | Sin permiso adicional |

---

## Reglas de Negocio (ExpedienteService)

**Archivo:** `backend/expedientes/services.py`
**Clase:** `ExpedienteService` (solo métodos estáticos)

### `validar_datos(data)`

Lanza `ValidationError` si las reglas no se cumplen.

#### Persona Natural (`tipo_persona == "NATURAL"`) — DNI

| Regla | Validación |
|-------|------------|
| Solo números | `dni.isdigit()` |
| Longitud exacta | `len(dni) == 8` |

#### Persona Jurídica (`tipo_persona == "JURIDICA"`) — RUC

| Regla | Validación |
|-------|------------|
| Solo números | `ruc.isdigit()` |
| Longitud exacta | `len(ruc) == 11` |

#### Colegiado (`tipo_persona == "COLEGIADO"`) — CIP

| Regla | Validación |
|-------|------------|
| Solo números | `cip.isdigit()` |
| Longitud | `3 <= len(cip) <= 10` |

#### Validaciones Comunes

| Campo | Regla |
|-------|-------|
| `telefono` | Solo números, `7 <= len(telefono) <= 9` |
| `numero_documento` | Mínimo 3 caracteres |

**Nota:** `tipo_documento` y `numero_folios` no tienen validación en el service (se asumen correctos por el serializer field).

### `generar_id_publico()`

```python
def generar_id_publico():
    fecha = timezone.now().strftime("%Y%m%d")
    aleatorio = secrets.token_hex(4).upper()
    return f"LIMA-{fecha}-{aleatorio}"
```

**Formato resultado:** `LIMA-20260120-A1B2C3D4`

| Componente | Descripción |
|------------|-------------|
| `LIMA` | Literal fijo (código de sede) |
| `YYYYMMDD` | Fecha actual |
| `HEX4` | 4 bytes en hex mayúsculas (8 caracteres) |

**Seguridad:** Usa `secrets.token_hex(4)` (crypto-safe random). No es secuencial ni predecible.

---

## Carga de Archivos

### Parser Configurado (Global)

El proyecto usa `NestedMultiPartParser` de `drf_nested_forms` configurado globalmente. Esto permite enviar datos JSON + archivos en la misma request (multipart).

### Archivo Principal (`archivo_principal`)

- **Campo en modelo:** `FileField(upload_to=ruta_archivo_principal)`
- **En serializer mutation:** Campo estándar `FileField`
- **Recibido como:** archivo multipart (key: `archivo_principal`)
- **Almacenamiento:** `expedientes/<id_publico>/principal/<uuid>.pdf`

### Anexos (`anexos`)

**Método:** JSON array con metadata de archivos (NO son archivos multipart en el payload principal).

**Recibido como:**
```json
{
  "anexos": [
    { "archivo_anexo": "<file_id_o_path>", "descripcion": "Factura enero" },
    { "archivo_anexo": "<file_id_o_path>", "descripcion": "Recibo pago" }
  ]
}
```

**Procesamiento:** `AnexosMixin.procesar_anexos()` recibe la lista y crea registros `ExpedienteArchivoAnexo`.

**Almacenamiento:** `expedientes/<id_publico>/anexos/<uuid>.ext`

**Nota sobre archivo_anexo en payload:** El campo espera un archivo. La implementación de `AnexosMixin` debe consultarse en `common/utils/mixins/anexos.py` para entender cómo maneja el upload real (puede usar IDs de archivos ya subidos o multipart inline).

### Seguridad en Nombres

Ver sección correspondiente en `modelos-y-bd.md`. Los archivos se renombran a UUID antes de guardar.

---

## Sistema de Permisos

### DjangoModelPermissionsConMensaje

**Archivo:** `backend/expedientes/permissions/django_permissions_coment.py`

Variante de `DjangoModelPermissions` con mensajes de error personalizados. Es el permiso base para TODOS los grupos en ambos ViewSets.

### Permisos por Rol (Expediente)

| Archivo Permission | Clase | Descripción |
|-------------------|-------|-------------|
| `permissions/rol/expediente/base.py` | `MesaDePartesExpedientePermission` | Permiso base para operación en Mesa de Partes. |

### Permisos por Rol (ExpedienteArchivoAnexo)

| Archivo Permission | Clase | Descripción |
|-------------------|-------|-------------|
| `rol/expediente_archivo_anexo/recepcion_mesa_de_partes_permissions.py` | `RecepcionMesaDePartesExpedienteArchivoAnexoPermission` | Permiso para recepción de anexos. |
| `rol/expediente_archivo_anexo/supervisor_mesa_de_partes.py` | `SupervisorMesaDePartesExpedienteArchivoAnexoPermission` | Permiso para supervisores. |
| `rol/expediente_archivo_anexo/encargado_de_area.py` | `EncargadoAreaExpedienteArchivoAnexoPermission` | Permiso para encargados de área. |

**Arquitectura de permisos:** Cada grupo tiene su archivo de permiso dedicado bajo `permissions/rol/`. Esto sigue el patrón de permisos granulares por rol.

---

## Mixins Compartidos

Los serializers de Expediente dependen de mixins definidos en `common/utils/mixins/`:

### `SanitizeEmptyStringMixin`

- **Propósito:** Previene que strings vacíos (`""`) se guarden como strings vacíos en campos que esperan `null`.
- **Aplicación:** Convierte `""` → `null` antes de la validación del serializer.

### `JsonPayloadMixin`

- **Propósito:** Permite que el body de la request sea JSON puro (además de multipart).
- **Aplicación:** Necesario para recibir `anexos` y `antecedentes` como arrays/dicts JSON.

### `AnexosMixin`

- **Propósito:** Abstrae la lógica de creación de registros hijos (ExpedienteArchivoAnexo).
- **Configuración:** `child_model = ExpedienteArchivoAnexo`, `fk_field = 'expediente'`
- **Método:** `procesar_anexos(instance, items_anexos)` — itera sobre la lista y crea/asocia registros.

### `RelationshipDiffMixin`

- **Propósito:** Maneja actualizaciones parciales de relaciones M2M con patrón delta.
- **Método:** `process_m2m_diff(instance, related_manager_name, data, ...)`
- **Formato de datos:** `{ "add": [uuids], "remove": [uuids] }`
- **Aplicación en Expediente:** Campo `antecedentes` (M2M self-referential).

### `SanitizeModelMixin`

- **Propósito:** Aplica sanitización de inputs a nivel de modelo (XSS, inyecciones).
- **Aplicación:** Expediente y ExpedienteArchivoAnexo heredan de este mixin.

---

## Transacciones Atómicas

### Create (`ExpedienteViewSet.create`)

```python
def create(self, request, *args, **kwargs):
    with transaction.atomic():
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expediente = serializer.save()  # Puede crear anexos
    
    read_serializer = ExpedienteQuerySerializer(expediente, ...)
    return Response(read_serializer.data, status=status.HTTP_201_CREATED)
```

**Garantía:** Si falla la creación de anexos o cualquier operación dentro de `serializer.save()`, se revierte la creación del expediente.

### Update (`ExpedienteViewSet.update`)

```python
def update(self, request, *args, **kwargs):
    partial = kwargs.pop('partial', False)
    instance = self.get_object()
    
    with transaction.atomic():
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        expediente = serializer.save()
    
    read_serializer = ExpedienteQuerySerializer(expediente, ...)
    return Response(read_serializer.data)
```

**Garantía:** La actualización parcial (PATCH) también está protegida atómicamente.

**Nota:** El serializer internally también usa `transaction.atomic()` en sus métodos `create`/`update` (con `with transaction.atomic():` en las líneas 145 y 172). Esto genera transacciones anidadas (savepoints), lo cual es correcto.

---

## Acciones Personalizadas (Actions)

### `creadas` — Expedientes del Usuario

```python
@action(detail=False, methods=["get"], url_path="creadas")
def creadas(self, request):
    qs = Expediente.objects.filter(creado_por=request.user).order_by("-fecha_creacion")
    return self._paginar_queryset(qs)
```

**Endpoint:** `GET /api/expedientes/creadas/`
**Filtro:** Solo expedientes donde `creado_por == request.user`
**Orden:** `-fecha_creacion` (más reciente primero)
**Respuesta:** Paginada

### `creadas_sin_solicitud` — Expedientes Sin Trámite

```python
@action(detail=False, methods=["get"], url_path="creadas-sin-solicitud")
def creadas_sin_solicitud(self, request):
    qs = Expediente.objects.filter(
        creado_por=request.user, 
        solicitud__isnull=True
    ).distinct().order_by("-fecha_creacion")
    return self._paginar_queryset(qs)
```

**Endpoint:** `GET /api/expedientes/creadas-sin-solicitud/`
**Filtro:** `creado_por == request.user` AND `solicitud IS NULL`
**Caso de uso:** Expedientes ingresados pero que aún no tienen un flujo de trámite asignado.
**Orden:** `-fecha_creacion`
**Respuesta:** Paginada

---

## Filtrado y Búsqueda

### Búsqueda Textual (SearchFilter)

```python
search_fields = [
    "id_publico",   # Código visible LIMA-YYYYMMDD-XXXX
    "dni",          # DNI del solicitante
    "ruc",          # RUC de la empresa
    "apellidos",    # Apellidos
    "nombres",      # Nombres
    "numero_documento",  # Número de documento
    "cip"           # CIP del colegiado
]
```

**Uso:** Filter backend de DRF (`SearchFilter`). Requiere parámetro `search=` en la query string.

### Ordenamiento (OrderingFilter)

```python
ordering_fields = ["fecha_creacion", "id_publico"]
ordering = ["-fecha_creacion"]  # Default: más reciente primero
```

### Campos RW (Read-Write) en Query Serializer

Todos los campos del `ExpedienteQuerySerializer` son `read_only_fields = fields`, por lo que el serializer de query NO acepta escrituras.

---

*Documento generado del código fuente en `backend/expedientes/views.py`, `backend/expedientes/serializers.py`, `backend/expedientes/services.py` y `backend/expedientes/urls.py`.*
