# Módulo Expedientes — Modelos y Base de Datos

## Índice

1. [Visión General](#visión-general)
2. [Modelo `Expediente`](#modelo-expediente)
3. [Modelo `ExpedienteArchivoAnexo`](#modelo-expedientearchivoanexo)
4. [Modelo `HistoricalExpediente`](#modelo-historicalexpediente)
5. [Choices y Dominios](#choices-y-dominios)
6. [Validaciones a Nivel Base de Datos](#validaciones-a-nivel-base-de-datos)
7. [Relaciones](#relaciones)
8. [Seguridad en Almacenamiento de Archivos](#seguridad-en-almacenamiento-de-archivos)
9. [Auditoría con simple-history](#auditoría-con-simple-history)

---

## Visión General

El módulo Expedientes gestiona los documentos oficiales del sistema de Mesa de Partes del Colegio de Ingenieros del Perú (CIP). Cada expediente representa un trámite ingresante con su archivo principal y opcionalmente múltiples anexos.

**Aplicación Django:** `backend/expedientes/`
**Modelos:** 3 (Expediente, ExpedienteArchivoAnexo, HistoricalExpediente)
**Auditoría:** simple-history (tracks cambios en Expediente)

---

## Modelo `Expediente`

**Tabla en BD:** `expedientes_expediente`
**PK:** `id` (UUID, no editable por el usuario)

### Campos

| Campo | Tipo BD | Constraints | Descripción |
|-------|---------|-------------|-------------|
| `id` | `uuid` | PK, `default=uuid.uuid4`, `editable=False` | UUID interno como clave primaria. No se expone al frontend. |
| `id_publico` | `varchar(25)` | `unique=True`, `editable=False` | Código visible para el usuario. Formato: `LIMA-YYYYMMDD-HEX4`. Generado por `ExpedienteService.generar_id_publico()`. |
| `tipo_persona` | `varchar(20)` | `choices=TIPO_PERSONA_CHOICES` | Clasificación del solicitante: Natural, Jurídica o Colegiado. |
| `dni` | `varchar(20)` | `null=True`, `blank=True` | DNI del solicitante (solo para `NATURAL`). 8 dígitos numéricos. |
| `ruc` | `varchar(20)` | `null=True`, `blank=True` | RUC de la empresa (solo para `JURIDICA`). 11 dígitos numéricos. |
| `cip` | `varchar(20)` | `null=True`, `blank=True` | CIP del ingeniero Colegiado (solo para `COLEGIADO`). 3-10 dígitos numéricos. |
| `razon_social` | `varchar(200)` | `null=True`, `blank=True` | Razón social (solo para `JURIDICA`). |
| `apellidos` | `varchar(200)` | nullable | Apellidos del solicitante natural o representante legal. |
| `nombres` | `varchar(200)` | nullable | Nombres del solicitante natural o representante legal. |
| `telefono` | `varchar(200)` | `null=True`, `blank=True` | Teléfono de contacto. 7-9 dígitos numéricos. |
| `correo` | `varchar(200)` | `null=True`, `blank=True` | Correo electrónico de contacto. |
| `tipo_documento` | `varchar(50)` | `choices=TIPO_DOCUMENTO_CHOICES` | Clasificación del documento principal ingresado. |
| `numero_documento` | `varchar(50)` | Not null | Número del documento de referencia. Mínimo 3 caracteres. |
| `numero_folios` | `integer` | `PositiveIntegerField` | Cantidad de folios del expediente. |
| `asunto` | `varchar(300)` | Not null | Resumen del motivo del trámite. |
| `archivo_principal` | `varchar(100)` | `FileField` con `upload_to=ruta_archivo_principal` | Archivo PDF/del documento principal. Se guarda en `expedientes/<id_publico>/principal/`. |
| `observaciones` | `text` | `null=True`, `blank=True`, `max_length=2000` | Notas opcionales del operador. |
| `creado_por` | `fk -> auth_user` | `on_delete=PROTECT`, `related_name=expedientes_creados` | Usuario que creó el expediente. Protegido: no se puede eliminar un usuario con expedientes. |
| `modificado_por` | `fk -> auth_user` | `on_delete=PROTECT`, `related_name=expedientes_modificados`, `null=True` | Usuario que hizo la última modificación. |
| `fecha_creacion` | `datetime` | `auto_now_add=True` | Timestamp de creación. No editable. |
| `fecha_actualizacion` | `datetime` | `auto_now=True` | Timestamp de última modificación. Se actualiza automáticamente. |
| `history` | (simple-history) | Auto-generado | Relación inversa a `HistoricalExpediente` para auditoría. |
| `antecedentes` | `m2m -> self` | `symmetrical=False`, `blank=True`, `related_name=consecuentes` | Expedientes previos relacionados. Relación auto-referencial no simétrica (un expediente puede tener varios antecedentes). |

### Notas de Diseño

- **Sin `clean()` ni `save()` override**: La validación de reglas de negocio y la generación de `id_publico` se delegan al `ExpedienteService`. Los modelos son "pasivos".
- **Mixin `SanitizeModelMixin`**: Aplica sanitización de inputs a nivel de modelo.
- **`__str__` duplicado** (líneas 82 y 85): Bug conocido — ambos métodos son idénticos; el segundo sobrescribe al primero sin efecto.

---

## Modelo `ExpedienteArchivoAnexo`

**Tabla en BD:** `expedientes_expedientearchivoanexo`
**PK:** `id` (UUID)

### Campos

| Campo | Tipo BD | Constraints | Descripción |
|-------|---------|-------------|-------------|
| `id` | `uuid` | PK, `default=uuid.uuid4`, `editable=False` | UUID interno. |
| `expediente` | `fk -> Expediente` | `on_delete=CASCADE`, `related_name=archivos_anexados` | Expediente padre. Si se elimina el expediente, se eliminan sus anexos en cascada. |
| `archivo_anexo` | `varchar(100)` | `FileField` con `upload_to=ruta_archivo_anexo` | Archivo anexo. Se guarda en `expedientes/<id_publico>/anexos/`. |
| `nombre_original` | `varchar(255)` | `null=True`, `blank=True` | Nombre original del archivo antes del renombrado de seguridad. |
| `descripcion` | `varchar(200)` | `blank=True` | Descripción opcional del anexo. |
| `fecha_creacion` | `datetime` | `auto_now_add=True` | Timestamp de creación. |

### Notas de Diseño

- **`save()` override**: Captura el nombre original del archivo ANTES de que Django lo renombre con UUID. Luego ejecuta `full_clean()`.
- **Seguridad en nombres de archivo**: El archivo físico se renombra a un UUID aleatorio; el `nombre_original` preserva el nombre original para exibição no frontend.

---

## Modelo `HistoricalExpediente`

**Tabla en BD:** `expedientes_historicalexpediente`
**PK:** `history_id` (AutoField)

Modelo auto-generado por `django-simple-history`. Registra cada cambio (creación, modificación, eliminación) en la tabla `Expediente`.

### Campos Principales

| Campo | Tipo BD | Descripción |
|-------|---------|-------------|
| `history_id` | `AutoField` | PK del registro histórico. |
| `history_date` | `datetime` | Timestamp del cambio. Indexado. |
| `history_type` | `varchar(1)` | `'+'` = Created, `'~'` = Changed, `'-'` = Deleted. |
| `history_user` | `fk -> auth_user` | Usuario que realizó el cambio (llena desde `request.user`). |
| `id_publico` | `varchar(25)` | Indexado (`db_index=True`), no único (puede repetirse en el tiempo). |

---

## Choices y Dominios

### `TIPO_PERSONA_CHOICES`

| Valor DB | Display |
|----------|---------|
| `NATURAL` | Persona Natural |
| `JURIDICA` | Persona Jurídica |
| `COLEGIADO` | Ingeniero Colegiado |

### `TIPO_DOCUMENTO_CHOICES`

| Valor DB | Display |
|----------|---------|
| `INVITACION` | Invitación |
| `ACTA_SESION_ORDINARIA` | Acta de Sesión Ordinaria |
| `CARTA` | Carta |
| `CARTA_MULTIPLE` | Carta Múltiple |
| `CARTA_NOTARIAL` | Carta Notarial |
| `CEDULA_NOTIFICACION` | Cédula de Notificación |
| `DISPOSICION_FISCAL` | Disposición Fiscal |
| `FACTURA` | Factura |
| `INFORME_VALORACION` | Informe de Valoración |
| `INFORME_PERICIAL_PARTE` | Informe Pericial de Parte |
| `OFICIO` | Oficio |
| `OFICIO_CIRCULAR` | Oficio Circular |
| `OFICIO_MULTIPLE` | Oficio Múltiple |
| `OPINION` | Opinión |
| `SOLICITUD` | Solicitud |

---

## Validaciones a Nivel Base de Datos

### Unique Constraints

| Campo | Tabla | Constraint |
|-------|-------|------------|
| `id_publico` | `expedientes_expediente` | `UNIQUE` |

### Foreign Key Constraints

| Campo | Tabla HIJO | Tabla PADRE | on_delete | Efecto |
|-------|------------|-------------|-----------|--------|
| `creado_por` | `expedientes_expediente` | `auth_user` | `PROTECT` | Impide eliminar usuario si tiene expedientes creados. |
| `modificado_por` | `expedientes_expediente` | `auth_user` | `PROTECT` | Impide eliminar usuario si tiene expedientes modificados. |
| `expediente` | `expedientes_expedientearchivoanexo` | `expedientes_expediente` | `CASCADE` | Al eliminar un expediente, se eliminan sus anexos. |

### Not Null Constraints

- `tipo_persona`, `tipo_documento`, `numero_documento`, `numero_folios`, `asunto`, `archivo_principal`, `creado_por`, `fecha_creacion`, `fecha_actualizacion` en `Expediente`.
- `expediente`, `archivo_anexo`, `fecha_creacion` en `ExpedienteArchivoAnexo`.

### Positive Integer Constraints

- `numero_folios` usa `PositiveIntegerField` (no permite valores negativos o cero).

### On Delete PROTECT

- `creado_por` y `modificado_por` usan `PROTECT` para prevenir eliminación de usuarios con expediente activos.

---

## Relaciones

### Expediente → Expediente (Auto-referencial M2M)

```
Expediente.antecedentes (M2M)
  └── Relaciona un expediente con sus expedientes antecedentes
  └── related_name='consecuentes' permite:
        expediente.consecuentes.all()  # Obtener expedientes que lo tienen como antecedente
```

**Tabla intermedia automática de Django:** `expedientes_expediente_antecedentes` (generada por Django para M2M).

### Expediente → ExpedienteArchivoAnexo (1 → N)

```
Expediente.archivos_anexados (reverse M2M)
  └── Un Expediente puede tener N archivos anexos
```

### Expediente → User (N → 1)

```
Expediente.creado_por (FK) → User
Expediente.modificado_por (FK) → User
```

### Expediente → Solicitud (N → 1, opcional)

```
Expediente.solicitud (FK, implied from views.py line 34: select_related('solicitud'))
  └── Relación implícita con Solicitud (no visible en models.py directamente)
```

---

## Seguridad en Almacenamiento de Archivos

### Función `ruta_archivo_principal`

```python
def ruta_archivo_principal(instance, filename):
    ext = filename.split('.')[-1]
    filename_seguro = f"{uuid.uuid4()}.{ext}"
    return os.path.join(f"expedientes/{instance.id_publico}/principal/", filename_seguro)
```

**Pattern:** `expedientes/<id_publico>/principal/<uuid>.ext`
**Medidas de seguridad:**
1. **UUID como nombre**: El nombre original del archivo NO se usa. Previene path traversal y exposición de nombres originales.
2. **Carpeta por expediente**: Cada expediente tiene su propia carpeta, aislando archivos.
3. **`id_publico` como carpeta**: Permite identificar rápidamente archivos de un expediente por su código visible.

### Función `ruta_archivo_anexo`

```python
def ruta_archivo_anexo(instance, filename):
    ext = filename.split('.')[-1]
    filename_seguro = f"{uuid.uuid4()}.{ext}"
    return os.path.join(f"expedientes/{instance.expediente.id_publico}/anexos/", filename_seguro)
```

**Pattern:** `expedientes/<id_publico>/anexos/<uuid>.ext`
**Diferencia con principal:** Usa `instance.expediente.id_publico` (accede al padre para obtener el código público).

---

## Auditoría con simple-history

El modelo `Expediente` hereda de `HistoricalRecords` (`simple-history`):

```python
history = HistoricalRecords()
```

**Comportamiento:**
- Cada `Expediente` creado/modificado/eliminado genera un registro en `HistoricalExpediente`.
- `history_user` se llena automáticamente si se configura el middleware de simple-history.
- `history_date` registra el momento del cambio.
- `history_type`: `'+'` (created), `'~'` (changed), `'-'` (deleted).

**Tabla:** `expedientes_historicalexpediente`

**No aplica a `ExpedienteArchivoAnexo`**: Este modelo NO tiene auditoría de simple-history.

---

## Migraciones Clave

| Migration | Cambio |
|-----------|--------|
| `0001_initial` | Crea tablas `Expediente`, `ExpedienteArchivoAnexo`, `HistoricalExpediente` |
| `0005_alter_expediente_id_publico_and_more` | Extiende `id_publico` de `max_length=20` a `max_length=25` para soportar el formato `LIMA-YYYYMMDD-HEX4` |
| `0007_expediente_antecedentes` | Añade M2M `antecedentes` a `Expediente` |

---

*Documento generado del código fuente en `backend/expedientes/models.py`, `backend/expedientes/services.py` y migraciones.*
