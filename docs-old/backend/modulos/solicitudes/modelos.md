# Modelos del Módulo Solicitudes

## 1. Modelo `Solicitud`

### Tabla Fílica

```
Solicitud (id: UUID)
├── expediente: FK → Expediente (1:1, PROTECT)
├── usuario_asignado: FK → User (N:1, PROTECT, nullable)     ← Gestor actual
├── area_responsable: FK → Area (N:1, PROTECT, nullable)      ← Bandeja por área [V2]
├── prioridad: VARCHAR(20)                                    ← NORMAL | ALTA | CRITICA
├── usuarios_adjuntados: M2M → User (through UsuarioSolicitudAdjuntado)
├── creado_por: FK → User (N:1, PROTECT)
├── modificado_por: FK → User (N:1, PROTECT)
├── estado: VARCHAR(20)                                       ← EstadosSolicitud.CHOICES
├── finalizado: BOOLEAN (default: False)
├── fecha_creacion: DATETIME (auto_now_add)
├── fecha_actualizacion: DATETIME (auto_now)
├── fecha_limite: DATETIME (nullable)
├── fecha_cierre: DATETIME (nullable)
├── id_publico: VARCHAR(25) (unique, editable=False)          ← LIMA-2026-...
└── history: HistoricalRecords (auditoría simple-history)
```

### Campos Clave

| Campo | Tipo | Nullable | Descripción |
|-------|------|----------|-------------|
| `id` | `UUID` | No | PK interno; nunca se expone en URLs públicas |
| `id_publico` | `VARCHAR(25)` | No | Código legible `LIMA-2026-XXXXX`; heredado del Expediente |
| `expediente` | `FK → Expediente` | No | Relación 1:1 obligatoria; la Solicitud nace del Expediente |
| `usuario_asignado` | `FK → User` | Sí | Gestor individual que tiene la solicitud en su bandeja personal [V2] |
| `area_responsable` | `FK → Area` | Sí | Bandeja de entrada grupal por área; coexiste con `usuario_asignado` [V2] |
| `prioridad` | `VARCHAR(20)` | No | `NORMAL` (default) / `ALTA` / `CRITICA` |
| `usuarios_adjuntados` | `M2M → User` | — | Colaboradores adicionales mediante tabla intermedia |
| `estado` | `VARCHAR(20)` | No | Uno de los 5 estados de `EstadosSolicitud` |
| `finalizado` | `BOOLEAN` | No | Flag de cierre; controlado por el Encargado de Área al llegar a `CERRADO` |
| `fecha_limite` | `DATETIME` | Sí | SLA calculado en `SolicitudService.preparar_datos_creacion` (default: +2 días) |
| `fecha_cierre` | `DATETIME` | Sí | Se inyecta automáticamente cuando `finalizado` pasa a `True` |
| `history` | `HistoricalRecords` | — | Auditoría automática de todos los cambios de estado |

### Índices y Restricciones

- **PK**: `id` (UUID, no secuencial)
- **UQ**: `id_publico` (garantiza unicidad del código público)
- **FK PROTECT**: `expediente`, `usuario_asignado`, `area_responsable`, `creado_por`, `modificado_por`
- **Auditoría**: `simple_history` graba cada versión en `historicalsolicitud`

---

## 2. Modelo `SolicitudArchivoAnexo`

```
SolicitudArchivoAnexo (id: UUID)
├── solicitud: FK → Solicitud (N:1, CASCADE)
├── archivo_anexo: FILE (upload_to: ruta_anexo_solicitud)
└── descripcion: VARCHAR(200)
```

### Función de Ruta Segura

```python
def ruta_anexo_solicitud(instance, filename):
    ext = filename.split('.')[-1]
    filename_seguro = f"{uuid.uuid4()}.{ext}"
    return os.path.join(f"solicitudes/{instance.solicitud.id_publico}/anexos/", filename_seguro)
```

- Guarda en: `solicitudes/<id_publico>/anexos/<uuid>.pdf`
- El archivo físico se renombra con UUID para evitar colisiones y path traversal

---

## 3. Modelo `ComentarioSolicitud` (Árbol de Comentarios)

### Tabla Fílica

```
ComentarioSolicitud (id: UUID)
├── solicitud: FK → Solicitud (N:1, CASCADE)
├── usuario: FK → User (N:1, CASCADE)
├── parent: FK → self (N:1, nullable)     ← Respuesta a otro comentario
├── texto: TEXT
├── fecha_creacion: DATETIME (auto_now_add)
└── history: HistoricalRecords
```

### Estructura de Árbol (Parent-Child)

```
Solicitud
└── Comentario (root-1) [parent=null]
    ├── Comentario (reply-1.1) [parent=root-1]
    │   └── Comentario (reply-1.1.1) [parent=reply-1.1]
    └── Comentario (reply-1.2) [parent=root-1]
└── Comentario (root-2) [parent=null]
```

- `parent=null` → comentario de primer nivel (hilo raíz)
- `parent=<UUID>` → respuesta dentro de un hilo
- El `related_name="respuestas"` permite consultar `comentario.respuestas.all()`
- **Inmutabilidad**: no existe endpoint de UPDATE/DELETE en `ComentarioSolicitudViewSet`

---

## 4. Modelo `ComentarioSolicitudArchivoAnexo`

```
ComentarioSolicitudArchivoAnexo (id: UUID)
├── comentario: FK → ComentarioSolicitud (N:1, CASCADE)
├── archivo_anexo: FILE (upload_to: ruta_anexo_comentario)
└── descripcion: VARCHAR(200)
```

### Función de Ruta Segura

```python
def ruta_anexo_comentario(instance, filename):
    ext = filename.split('.')[-1]
    filename_seguro = f"{uuid.uuid4()}.{ext}"
    solicitud_id = instance.comentario.solicitud.id_publico
    comentario_id = instance.comentario.id
    return os.path.join(f"solicitudes/{solicitud_id}/comentarios/{comentario_id}/", filename_seguro)
```

---

## 5. Modelo `UsuarioSolicitudAdjuntado` (Tabla Intermedia M2M)

```
UsuarioSolicitudAdjuntado (id: UUID)
├── solicitud: FK → Solicitud (N:1, CASCADE)
├── usuario: FK → User (N:1, CASCADE)
└── history: HistoricalRecords
```

- Relación M2M explícita con `through` para permitir auditoría via `simple_history`
- Se manipula mediante el patrón diff (`{ add: [...], remove: [...] }`) en `SolicitudMutationSerializer`

---

## Resumen de Relaciones

```
Expediente ──1:1──► Solicitud
                         │
                         ├──1:N──► SolicitudArchivoAnexo
                         │
                         ├──1:N──► ComentarioSolicitud
                         │              │
                         │              ├──1:N──► ComentarioSolicitudArchivoAnexo
                         │              │
                         │              └──N:1──► self (parent)
                         │
                         └──M2M──► User (through UsuarioSolicitudAdjuntado)
```
