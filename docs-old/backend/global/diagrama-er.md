# Visión Global del Backend — Diagrama ER Completo

> **Aplicación**: Mesa de Partes CIP
> **Versión del documento**: 1.0
> **Última actualización**: Agosto 2026

---

## 1. Diagrama Entidad-Relación (Mermaid)

```mermaid
erDiagram
    USER {
        int id PK
        string username
        string email
        string password
        string first_name
        string last_name
        boolean is_staff
        boolean is_active
        datetime date_joined
    }

    PERFIL_USUARIO {
        int id PK
        int user_id FK
        int area_id FK
        int cargo_id FK
        int jefe_id FK
    }

    AREA {
        int id PK
        string nombre
        string descripcion
        string slug
    }

    CARGO {
        int id PK
        string nombre
        int nivel
    }

    EXPEDIENTE {
        uuid id PK
        string id_publico
        string tipo_persona
        string dni
        string ruc
        string cip
        string razon_social
        string apellidos
        string nombres
        string telefono
        string correo
        string tipo_documento
        string numero_documento
        int numero_folios
        string asunto
        file archivo_principal
        text observaciones
        int creado_por_id FK
        int modificado_por_id FK
        datetime fecha_creacion
        datetime fecha_actualizacion
    }

    HISTORICAL_EXPEDIENTE {
        uuid id PK
        string id_publico
        json history
        int history_user_id
        datetime history_date
        string history_type
    }

    EXPEDIENTE_ARCHIVO_ANEXO {
        uuid id PK
        int expediente_id FK
        file archivo_anexo
        string nombre_original
        string descripcion
        datetime fecha_creacion
    }

    SOLICITUD {
        uuid id PK
        string id_publico
        int expediente_id FK
        int usuario_asignado_id FK
        int area_responsable_id FK
        string prioridad
        string estado
        boolean finalizado
        datetime fecha_limite
        datetime fecha_cierre
        int creado_por_id FK
        int modificado_por_id FK
        datetime fecha_actualizacion
        datetime fecha_creacion
    }

    HISTORICAL_SOLICITUD {
        uuid id PK
        string id_publico
        int expediente_id
        json history
        int history_user_id
        datetime history_date
        string history_type
    }

    SOLICITUD_ARCHIVO_ANEXO {
        uuid id PK
        int solicitud_id FK
        file archivo_anexo
        string descripcion
        datetime fecha_creacion
    }

    COMENTARIO_SOLICITUD {
        uuid id PK
        int solicitud_id FK
        int usuario_id FK
        int parent_id FK
        text texto
        datetime fecha_creacion
    }

    HISTORICAL_COMENTARIO_SOLICITUD {
        uuid id PK
        int solicitud_id
        json history
        int history_user_id
        datetime history_date
        string history_type
    }

    COMENTARIO_SOLICITUD_ARCHIVO_ANEXO {
        uuid id PK
        int comentario_id FK
        file archivo_anexo
        string descripcion
        datetime fecha_creacion
    }

    USUARIO_SOLICITUD_ADJUNTADO {
        uuid id PK
        int solicitud_id FK
        int usuario_id FK
        datetime history_date
    }

    GROUP {
        int id PK
        string name
    }

    USER_GROUPS {
        int id PK
        int user_id FK
        int group_id FK
    }

    GROUP_PERMISSIONS {
        int id PK
        int group_id FK
        int permission_id FK
    }

    USER ||--o| PERFIL_USUARIO : "OneToOne"
    PERFIL_USUARIO }o--|| AREA
    PERFIL_USUARIO }o--|| CARGO
    PERFIL_USUARIO }o--o| PERFIL_USUARIO : "jefe"
    AREA ||--o{ PERFIL_USUARIO
    CARGO ||--o{ PERFIL_USUARIO
    EXPEDIENTE }o--|| USER : "creado_por"
    EXPEDIENTE }o--o| USER : "modificado_por"
    EXPEDIENTE }o--o{ EXPEDIENTE : "antecedentes"
    EXPEDIENTE ||--o{ EXPEDIENTE_ARCHIVO_ANEXO
    EXPEDIENTE ||--|| SOLICITUD : "OneToOne"
    SOLICITUD }o--|| USER : "usuario_asignado"
    SOLICITUD }o--|| USER : "creado_por"
    SOLICITUD }o--o| USER : "modificado_por"
    SOLICITUD }o--o| AREA : "area_responsable"
    SOLICITUD ||--o{ SOLICITUD_ARCHIVO_ANEXO
    SOLICITUD ||--o{ COMENTARIO_SOLICITUD
    COMENTARIO_SOLICITUD }o--|| USER : "usuario"
    COMENTARIO_SOLICITUD }o--o| COMENTARIO_SOLICITUD : "parent"
    COMENTARIO_SOLICITUD ||--o{ COMENTARIO_SOLICITUD_ARCHIVO_ANEXO
    SOLICITUD }o--o{ USUARIO_SOLICITUD_ADJUNTADO
    USER ||--o{ USUARIO_SOLICITUD_ADJUNTADO
    USER }o--o{ GROUP
    GROUP ||--o{ USER_GROUPS
    USER_GROUPS }o--|| USER
    USER_GROUPS }o--|| GROUP
    GROUP ||--o{ GROUP_PERMISSIONS
    GROUP_PERMISSIONS }o--|| PERMISSION
```

---

## 2. Descripción de Tablas

### 2.1 App `usuarios`

| Tabla | Tipo | Primary Key | Foreign Keys |
|-------|------|-------------|--------------|
| `auth_user` | Built-in Django | `id` | — |
| `usuarios_permiso` | Modelo | `id` | — |
| `usuarios_cargo` | Modelo | `id` | — |
| `usuarios_area` | Modelo | `id` | — |
| `usuarios_perfilusuario` | Modelo | `id` | `user_id` → User, `area_id` → Area, `cargo_id` → Cargo, `jefe_id` → self |

### 2.2 App `expedientes`

| Tabla | Tipo | Primary Key | Foreign Keys |
|-------|------|-------------|--------------|
| `expedientes_expediente` | Modelo | `id` (UUID) | `creado_por_id` → User, `modificado_por_id` → User |
| `expedientes_expediente_antecedentes` | M2M auto-tabla | `id` | `from_expediente_id`, `to_expediente_id` → Expediente |
| `expedientes_expedientearchivoanexo` | Modelo | `id` (UUID) | `expediente_id` → Expediente |
| `historical_expediente` | SimpleHistory | `id` (UUID) | `expediente_ptr_id` → Expediente |

### 2.3 App `solicitudes`

| Tabla | Tipo | Primary Key | Foreign Keys |
|-------|------|-------------|--------------|
| `solicitudes_solicitud` | Modelo | `id` (UUID) | `expediente_id` → Expediente (1:1), `usuario_asignado_id` → User, `area_responsable_id` → Area, `creado_por_id` → User, `modificado_por_id` → User |
| `solicitudes_solicitudarchivoanexo` | Modelo | `id` (UUID) | `solicitud_id` → Solicitud |
| `solicitudes_comentariosolicitud` | Modelo | `id` (UUID) | `solicitud_id` → Solicitud, `usuario_id` → User, `parent_id` → self |
| `solicitudes_comentariosolicitudarchivoanexo` | Modelo | `id` (UUID) | `comentario_id` → ComentarioSolicitud |
| `solicitudes_usuariosolicitudadjuntado` | Modelo | `id` (UUID) | `solicitud_id` → Solicitud, `usuario_id` → User |
| `historical_solicitud` | SimpleHistory | `id` (UUID) | `solicitud_ptr_id` → Solicitud |
| `historical_comentariosolicitud` | SimpleHistory | `id` (UUID) | `comentariosolicitud_ptr_id` → ComentarioSolicitud |

---

## 3. Relaciones Clave Explicadas

### 3.1 Expediente → Solicitud (1:1)

```
Expediente (1) ←→ (1) Solicitud
       │                    │
       └── id_publico ←──────── id_publico (heredado)
       └── Se crea primero
       └── Un Expediente tiene UNA Solicitud
```

**Importante**: `on_delete=models.PROTECT` en la FK de Solicitud → Expediente. No se puede eliminar un Expediente si tiene una Solicitud asociada.

### 3.2 Solicitud → UsuarioAsignado (FK, nullable)

```
Solicitud → User (usuario_asignado)
     │
     └── En V2 puede ser NULL (solicitud en bandeja de área, sin asignar a persona)
```

### 3.3 AreaResponsable (FK)

```
Solicitud → Area (area_responsable)
     │
     └── Indica el área que debe atender la solicitud
     └── En V2 las bandejas se filtran por área del usuario
```

### 3.4 ComentarioSolicitud con Hilos (self-referential FK)

```
ComentarioSolicitud
    ├── texto: "Primera observación"
    ├── parent: NULL (es root)
    │
    ├── Respuesta 1 (parent: this)
    │       └── texto: "Respuesta a observación"
    │
    └── Respuesta 2 (parent: this)
            └── texto: "Otra respuesta"
```

### 3.5 UsuariosAdjuntos (M2M a través de tabla intermedia)

```
Solicitud ←── UsuarioSolicitudAdjuntado ──→ User
                 │
                 └── Permite agregar colaboradores a una solicitud
                 └── Similar a "cc" en un email
```

### 3.6 Expediente Antecedentes (M2M self-referential)

```
Expediente A ←── antecedentes ──→ Expediente B
     │
     └── A tiene como antecedente a B
     └── B no sabe de A (asimétrico, not symmetrical)
```

---

## 4. Tipos de Datos por Columna

### 4.1 UUIDs (Primary Keys seguras)

Todas las tablas de negocio principal usan:
```python
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
```

### 4.2 ID Público (Códigos legibles)

```python
id_publico = models.CharField(max_length=25, unique=True, editable=False)
# Formato: LIMA-2026-0001, LIMA-2026-0002, etc.
```

### 4.3 Choices (Enumeraciones)

**tipo_persona:**
```python
TIPO_PERSONA_CHOICES = [
    ("NATURAL", "Persona Natural"),
    ("JURIDICA", "Persona Jurídica"),
    ("COLEGIADO", "Ingeniero Colegiado"),
]
```

**prioridad:**
```python
PRIORIDAD_CHOICES = [
    ("NORMAL", "Normal"),
    ("ALTA", "Alta"),
    ("CRITICA", "Crítica"),
]
```

**estados (flujo de solicitudes):**
```python
ESTADOS_BASE = {
    "EN_GESTION_MP": {...},
    "REENVIO_MP": {...},
    "ENVIADO_A_AREA": {...},
    "EN_TRAMITE_AREA": {...},
    "CERRADO": {...},
}
```

---

## 5. Índices y Constraints

### 5.1 Índices Únicos

| Campo | Tipo | Razón |
|-------|------|-------|
| `auth_user.username` | Unique | Login único |
| `usuarios_area.slug` | Unique | Slugs URL-safe |
| `usuarios_permiso.nombre` | Unique | Permisos únicos |
| `usuarios_permiso.descripcion` | Unique | Slug de permiso único |
| `expedientes_expediente.id_publico` | Unique | Código visible único |
| `solicitudes_solicitud.id_publico` | Unique | Código visible único |

### 5.2 Foreign Keys con on_delete

| FK | on_delete | Razón |
|----|-----------|-------|
| PerfilUsuario.user | CASCADE | Si se elimina usuario, eliminar perfil |
| PerfilUsuario.area | SET_NULL | Área puede eliminarse, perfil queda sin área |
| Solicitud.expediente | PROTECT | No eliminar expediente con solicitudes activas |
| Solicitud.usuario_asignado | PROTECT | Mantener trazabilidad de asignación |
| Expediente.creado_por | PROTECT | Mantener auditoría de creación |
| ComentarioSolicitud.usuario | CASCADE | Si se elimina usuario, eliminar sus comentarios |

---

## 6. SimpleHistory: Tablas Shadow

Por cada modelo con `history = HistoricalRecords()`, Django crea una tabla `historical_<modelo>`:

```
solicitudes_solicitud          →  historical_solicitud
solicitudes_comentariosolicitud →  historical_comentariosolicitud
expedientes_expediente         →  historical_expediente
```

**Estructura de tabla histórica:**
```python
# Campos del modelo original
+ todos los campos del modelo

# Campos de auditoría SimpleHistory
+ id (shadow PK)
+ history_user (FK → User que hizo el cambio)
+ history_date (datetime)
+ history_type (+ = created, ~ = changed, - = deleted)
+ history_change_reason (nullable)
```

**Nota**: No hay `history` en `SolicitudArchivoAnexo`, `ComentarioSolicitudArchivoAnexo`, `UsuarioSolicitudAdjuntado`, ni `ExpedienteArchivoAnexo` — estos no rastrean cambios históricos.
