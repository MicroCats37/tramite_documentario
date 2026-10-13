# SAAA: Implementación en Django para Mesa de Partes

> **Estado:** Documento de arquitectura — no es implementación
> **Proyecto:** mesa-de-partes-final (CIP)
> **Referencia:** semana-ingenieria-mayo-2026 (Next.js)

---

## 1. Decisión corta

**Usar SAAA como storage externo con proxy local.** No reemplazar `FileField` globalmente. Para cada archivo:
1. Subir a SAAA vía API REST.
2. Guardar el `id` SAAA en un campo del modelo (no cambiar `archivo` FileField existente).
3. Exponer una URL proxy Django `/api/archivo/public/{id}` que decodifique base64 desde SAAA y sirva binario.

---

## 2. ¿Por qué SAAA necesita tratamiento especial y no basta con `FileField`?

`FileField` de Django es un campo que persiste archivos en el **storage backend configurado** (por defecto `FileSystemStorage`, i.e. disco local en `MEDIA_ROOT`). SAAA es un **microservicio externo** con su propia lógica:

| Aspecto | FileField Django | SAAA |
|---|---|---|
| **Storage** | Disco local (`media/`) | Microservicio HTTP (`172.16.93.83:9007`) |
| **Upload** | Django recibe el archivo, lo escribe en disco | POST multipart a `{SAAA_URL}/archivo/save` |
| **Descarga/consulta** | `request.build_absolute_uri(archivo.url)` → archivo directo | GET `{SAAA_URL}/archivo/find-by-id/{appId}/{id}` → **base64 en JSON** |
| **Identificador** | Ruta relativa en disco (`tramites/expedientes/uuid.pdf`) | ID entero o UUID devuelto por SAAA |
| **Registro previo** | No se necesita | Requiere POST `{SAAA_URL}/archivador/save` con `appId` y `tipoArchivadorId` |
| **Autenticación** | Integrada con Django auth | Variables de entorno compartidas (`SAAA_APP_ID`, etc.) |
| **Contenido** | Stream binario | Campo `bytes` con base64-encoded string |

**SAAA no es un filesystem.** No puedes usar `archivo.url` ni `archivo.read()`. Necesitas:
- HTTP client para subir (multipart)
- HTTP client para descargar (GET → decodificar base64 → binary response)
- Un endpoint proxy Django que oculte SAAA del frontend

---

## 3. Comparación Next.js vs Django

### Next.js (referencia — `semana-ingenieria-mayo-2026`)

```
Frontend
  │
  │ 1. FileInput selecciona archivo
  ▼
SaaaStorage.save(buffer, mime, domain, entityId)
  │ POST /archivo/save  (multipart: aplicacionId, usuarioId, tipoArchivoId, files)
  ▼
SAAA API
  │ Respuesta: [{ id, pathRelativo, nombreOriginal, extension }]
  ▼
 返 ─── URL proxy: /api/archivo/public/{id}
```

**Archivos clave:**
- `next/src/infra/storage/saaa-storage.ts` — implementa `StoragePort`, sube a SAAA, retorna `/api/archivo/public/{id}`
- `next/src/infra/storage/saaa-client.ts` — cliente puro para `findById`, `base64ToBuffer`, `extensionToMime`
- `next/src/app/api/archivo/public/[id]/route.ts` — proxy route: GET SAAA → decodifica base64 → binary response

**Flujo lectura:**
```
Frontend → GET /api/archivo/public/{id}
  → findById(id)  [SAAA]
  → { bytes: base64, nombreOriginal, extension }
  → base64ToBuffer(bytes)
  → NextResponse(new Uint8Array(buffer), { Content-Type, Content-Disposition })
```

### Django (mesa-de-partes-final)

El mismo flujo aplica, adaptado a Django Ninja:

```
Frontend
  │
  │ POST /api/solicitudes/ (con archivo en FormData)
  ▼
Django API Controller
  │ 1. Validar schema (sin tocar archivo todavía)
  │ 2. Extraer archivo del request
  │ 3. SAAAStorage.save(buffer, mime) → retorna id SAAA
  │ 4. Guardar { id_saaa, nombre_original, tipo_archivo } en modelo
  ▼
SAAA API
  │ POST /archivo/save  (multipart)
  │ GET /archivo/find-by-id/{appId}/{id}  (para descarga)
  ▼
 返 ─── GET /api/archivo/public/{id}  (proxy route Django)
```

**Equivalencias:**
| Concepto Next.js | Equivalente Django |
|---|---|
| `SaaaStorage.save()` | `SaaaStorageService.save()` (nuevo servicio en `infrastructure/`) |
| `saaa-client.ts` | `saaa_client.py` (módulo en `core/infrastructure/`) |
| `/api/archivo/public/[id]/route.ts` | `@router.get("/archivo/public/{id}")` en `core/presentation/routers/` |
| `StoragePort` interface | `AbstractStorageBackend` abstract class |
| `SAAA_URL`, `SAAA_APP_ID` env vars | Mismas — declaradas en `settings/base.py` |

---

## 4. Flujo de upload

### Paso 1 — Registrar/verificar el archivador (al iniciar la app o en startup)

```python
# En un comando de Django o durante el setup de la app
POST https://172.16.93.83:9007/api/v1/archivador/save
Content-Type: application/json

{
  "id": "mesa-partes-legacy",       # SAAA_APP_ID
  "tipoArchivadorId": "1",
  "autorizacion": True
}
```

> Este paso **solo se ejecuta una vez** por aplicación. Si el archivador ya existe, SAAA lo ignora o devuelve 200. Es idempotente.

### Paso 2 — Upload del archivo

```python
# En el servicio SAAA
POST https://172.16.93.83:9007/api/v1/archivo/save
Content-Type: multipart/form-data

fields:
  aplicacionId: "mesa-partes-legacy"   # SAAA_APP_ID
  usuarioId: "1"                        # ID del usuario logueado
  tipoArchivoId: "1"                    # 1 = documento general
  files: <binary del archivo>
```

**Respuesta:**
```json
[
  {
    "id": 42,
    "pathRelativo": "/mesa-partes-legacy/2026/09/archivo_abc123.pdf",
    "nombreOriginal": "mi_documento.pdf",
    "extension": ".pdf"
  }
]
```

### Paso 3 — Guardar en el modelo Django

En `ExpedienteArchivo` o `SolicitudArchivo`, **agregar un campo opcional** `saaa_id` que almacene el ID devuelto por SAAA:

```python
class ExpedienteArchivo(BaseModel):
    # ... campos existentes ...
    archivo = models.FileField(upload_to="tramites/expedientes/")  # se conserva para nuevos docs
    saaa_id = models.CharField(max_length=255, null=True, blank=True,
                                help_text="ID del archivo en SAAA (para legacy)")
```

> **No cambiar el `archivo` FileField existente.** Conservar para nuevos uploads que aún no usen SAAA. Solo populado para archivos migrated de legacy.

---

## 5. Flujo de lectura / visualización

### Endpoint proxy Django

```python
@router.get("/archivo/public/{archivo_id}", response=StreamingResponse)
def descargar_archivo_publico(request, archivo_id: str):
    """
    Proxy público para archivos almacenados en SAAA.
    GET /api/archivo/public/{id}
    → consulta SAAA GET /archivo/find-by-id/{SAAA_APP_ID}/{id}
    → decodifica base64 → responde como binary
    """
    saaa_url = settings.SAAA_URL
    app_id = settings.SAAA_APP_ID

    # 1. Consultar SAAA
    response = requests.get(
        f"{saaa_url}/archivo/find-by-id/{app_id}/{archivo_id}",
        timeout=30
    )

    if response.status_code == 404:
        raise Http404("Archivo no encontrado")

    data = response.json()
    # data = { id, nombreOriginal, extension, bytes: base64_string }

    # 2. Decodificar base64 → bytes
    file_bytes = base64.b64decode(data["bytes"])

    # 3. Determinar Content-Type
    content_type = extension_to_mime(data["extension"])

    # 4. Responder como binary
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{data["nombreOriginal"]}"',
            "Content-Length": str(len(file_bytes)),
            "Cache-Control": "public, max-age=86400",
        }
    )
```

### URL en el frontend

El frontend usa la misma URL que en Next.js:

```
GET /api/archivo/public/42
```

Y en el modelo `ExpedienteArchivo` presenter, se construye la URL:

```python
def _map_archivo(archivo: ExpedienteArchivo) -> dict:
    if archivo.saaa_id:
        url = f"/api/archivo/public/{archivo.saaa_id}"
    else:
        url = archivo.archivo.url  # fallback local
    return {
        "id": str(archivo.id),
        "url": request.build_absolute_uri(url),
        "nombre_original": archivo.nombre_original,
        "tipo_archivo": archivo.tipo_archivo,
    }
```

---

## 6. Cómo encaja con `FileField` existente

### Estrategia incremental (no disruptiva)

```
┌─────────────────────────────────────────────────────────────┐
│  Django STORAGES (config/settings/base.py)                    │
│  "default": FileSystemStorage → MEDIA_ROOT (sin cambios)     │
│                                                              │
│  ExpedienteArchivo / SolicitudArchivo                        │
│  ├── archivo: FileField (nuevos docs van a disco local)     │
│  └── saaa_id: CharField null (ID SAAA para docs legacy)     │
└─────────────────────────────────────────────────────────────┘
```

| Escenario | Storage | Campo usado |
|---|---|---|
| Nuevo documento (post-migración) | `FileField` → disco local | `archivo` |
| Documento migrado de legacy | SAAA (no toca `archivo`) | `saaa_id` |
| Consulta/descarga | Proxy SAAA → `/api/archivo/public/{saaa_id}` | `saaa_id` |
| Consulta/descarga local | `archivo.url` directo | `archivo` |

**No se toca `STORAGES` global.** No se crea un custom storage backend para SAAA. Se mantiene `FileField` como está.

---

## 7. Variables de entorno necesarias

```bash
# .env o variables de Docker

# ── SAAA (Sistema de Almacenamiento de Archivos) ──────────────
SAAA_URL=http://172.16.93.83:9007/api/v1
SAAA_APP_ID=mesa-partes-legacy          # debe coincidir con el id registrado en /archivador/save
SAAA_USUARIO_ID=1                       # usuario default para uploads (sysadmin)
SAAA_TIPO_ARCHIVO_ID=1                  # tipo de archivo default (1 = documento general)
SAAA_TIPO_ARCHIVADOR_ID=1              # tipo de archivador (1 = estándar)
```

> En `config/settings/base.py`, leer con `env()` igual que `DB_*` y `SECRET_KEY`.

---

## 8. Checklist de implementación futura

- [ ] **Infraestructura SAAA:**
  - [ ] Agregar variables `SAAA_*` a `config/settings/base.py`
  - [ ] Crear módulo `core/infrastructure/saaa_client.py` (cliente HTTP puro)
  - [ ] Crear clase `SaaaStorageBackend` que implemente protocolo de upload/download
  - [ ] Crear comando Django `register_saaa_archivador` para registrar la app una vez

- [ ] **Modelos:**
  - [ ] Agregar campo `saaa_id = CharField(max_length=255, null=True, blank=True)` a `ExpedienteArchivo`
  - [ ] Agregar campo `saaa_id` a `SolicitudArchivo`
  - [ ] Crear migración

- [ ] **API — Upload:**
  - [ ] Crear endpoint `@router.post("/archivo/upload")` en `core/presentation/routers/`
  - [ ] Integrar `SaaaStorageBackend.save()` en el flujo de creación de `ExpedienteArchivo` / `SolicitudArchivo`
  - [ ] Preservar `archivo` FileField para nuevos docs locales

- [ ] **API — Descarga/Proxy:**
  - [ ] Crear `@router.get("/archivo/public/{id}")` que consulte SAAA y decodifique base64
  - [ ] Mapear `saaa_id` → URL proxy en `ExpedientePresenter._map_archivo()`
  - [ ] Fallback: si no tiene `saaa_id`, usar `archivo.url` directo

- [ ] **Frontend:**
  - [ ] Ajustar `InputFileCollection` para subir a `/api/archivo/upload` (en lugar de FormData directo)
  - [ ] Asegurar que URLs de visualización usen `/api/archivo/public/{id}` uniformly

- [ ] **Migración legacy:**
  - [ ] `migracion_standalone.py` — modificar `_migrate_archivos()` para que por cada archivo legacy: 1) hacer upload a SAAA, 2) guardar el `saaa_id` retornado, 3) no escribir en disco local

- [ ] **Testing:**
  - [ ] Test unitario: `SaaaStorageBackend.save()` → verifica POST y parsing de respuesta
  - [ ] Test unitario: endpoint proxy → verifica decodificación base64 y headers
  - [ ] Test e2e: upload + descarga roundtrip

---

## 9. Riesgos y gotchas

### Riesgo 1: SAAA no disponible
**Impacto:** Upload o descarga falla.
**Mitigación:** El endpoint proxy debe responder 502 con mensaje claro. Considerar fallback a `archivo.url` si `saaa_id` es null.

### Riesgo 2: Archivos grandes / timeouts
**Impacto:** Upload multipart a SAAA puede exceder el timeout por defecto.
**Mitigación:** Configurar `timeout=120` segundos en el cliente HTTP y validar tamaño en el controller antes de subir.

### Riesgo 3: Base64 overhead
**Impacto:** SAAA devuelve archivos como base64 → JSON response puede ser ~33% más grande que el archivo original.
**Mitigación:** El proxy streaming декодирует base64 en chunks. No almacenar el JSON completo en memoria.

### Riesgo 4: ID de archivo SAAA como string público
**Impacto:** Exponer `saaa_id` en URLs permite acceso a archivos si se conoce el ID (no es guessable si es UUID).
**Mitigación:** SAAA usa IDs incrementales para algunos archivos y UUID para otros. Tratar como ID opaco; la autorización de acceso debe estar en la capa Django (el proxy solo sirve a usuarios autenticados).

### Gotcha: `archivador/save` es idempotente pero no es un GET
**Problema:** Solo se puede crear vía POST. No hay GET para verificar existencia antes de crear.
**Mitigación:** Intentar POST siempre; si el archivador ya existe, SAAA devuelve 200 sin error. Opcionalmente cachear en variable de entorno `SAAA_ARCHIVADOR_REGISTERED=true` tras el primer registro exitoso.

### Gotcha: `tipoArchivoId` y `tipoArchivadorId` son strings en el API
**Problema:** Algunos campos son `int` en el script Python pero strings en el multipart. El script usa `(None, valor)` para multipart y `{"tipoArchivadorId": "1"}` para JSON body.
**Mitigación:** Asegurar que el cliente Django envíe los valores correctos según el content-type.

### Gotcha: `pathRelativo` en respuesta incluye el appId
**Problema:** La respuesta `{pathRelativo: "/mesa-partes-legacy/2026/09/archivo.pdf"}` no se usa para construir la URL pública — se usa solo el `id`.
**Mitigación:** El `id` es el identificador público. No concatenar `pathRelativo` en la URL.

### Gotcha: El campo `archivo` FileField sigue escribiendo a disco
**Problema:** Los nuevos documentos siguen usando `FileField` (disco local), pero el flujo de migración legacy sube a SAAA.
**Mitigación:** Esto es intencional (estrategia incremental). Cuando TODOS los docs legacy estén migrados, se puede evaluar cambiar el storage backend global o mantener el dual indefinitely.

---

## 10. Referencias

- Script diagnóstico SAAA: `semana-ingenieria-mayo-2026/scripts/test-saaa-register-app.py`
- Storage Next.js: `semana-ingenieria-mayo-2026/next/src/infra/storage/saaa-storage.ts`
- Cliente Next.js: `semana-ingenieria-mayo-2026/next/src/infra/storage/saaa-client.ts`
- Proxy route Next.js: `semana-ingenieria-mayo-2026/next/src/app/api/archivo/public/[id]/route.ts`
- Modelos Django: `backend/modules/tramites/domain/models/expediente_archivo.py`, `solicitud_archivo.py`
- Storage config: `backend/config/settings/base.py` → `STORAGES` (línea 112-123)
- Migración legacy: `migracion_standalone.py` → `_migrate_archivos()` (línea 455)
