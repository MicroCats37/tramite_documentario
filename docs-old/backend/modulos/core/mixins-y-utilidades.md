# Módulo Core: Mixins y Utilidades

## Visión General

`common/utils/` contiene mixins reutilizables y utilidades que otras apps heredan o consumen. El directorio se estructura en:

```
common/utils/
├── mixins/
│   ├── sanitization.py   # 2 mixins
│   ├── relationships.py  # 1 mixin
│   ├── payload.py        # 1 mixin
│   └── anexos.py         # 1 mixin
├── schemas/
│   └── anexos.py         # Pydantic schema
├── permissions.py        # 1 mixin
└── constants/
    ├── solicitudes/
    └── expediente/
```

**Total: 5 Mixins + 1 Pydantic Schema + 1 Mixin de permisos = 7 artefactos reutilizables.**

---

## 1. SanitizeEmptyStringMixin

**Ubicación**: `common/utils/mixins/sanititization.py`

**Propósito**: En Serializers, convierte automáticamente cualquier string vacío (`""`) a `None` antes de la validación.

**Problema que resuelve**: Django/DRF permite que un campo opcional tenga dos estados semánticamente distintos: `NULL` en base de datos y `""` (empty string). Esto genera confusión y problemas de query (`WHERE campo = ''` vs `WHERE campo IS NULL`). Este mixin normaliza todo a `NULL`.

**Uso en el proyecto**:
```python
# backend/usuarios/serializers.py
class AreaSerializer(SanitizeEmptyStringMixin, serializers.ModelSerializer):
    ...
```

**Implementación**:
```python
class SanitizeEmptyStringMixin:
    def to_internal_value(self, data):
        # Si es dict/QueryDict, reemplaza "" por None en cada clave
        if isinstance(new_data, dict):
            for key, value in new_data.items():
                if value == "":
                    new_data[key] = None
        return super().to_internal_value(new_data)
```

**Aplicado a**: `AreaSerializer` (módulo `usuarios`).

---

## 2. SanitizeModelMixin

**Ubicación**: `common/utils/mixins/sanititization.py`

**Propósito**: En Models, convierte strings vacíos a `None` en campos que permiten `null=True` antes de guardar (`save()`).

**Problema que resuelve**: Lo mismo que el mixin de serializers, pero a nivel de modelo. Garantiza que la base de datos nunca reciba `""` en un campo que permite `NULL`.

**Uso en el proyecto**:
```python
# backend/usuarios/models.py
class Area(SanitizeModelMixin, models.Model):
    ...
```

**Implementación**:
```python
class SanitizeModelMixin:
    def save(self, *args, **kwargs):
        for field in self._meta.fields:
            # Solo CharField/TextField con null=True
            if isinstance(field, (models.CharField, models.TextField)) and field.null:
                if getattr(self, field.name) == "":
                    setattr(self, field.name, None)
        super().save(*args, **kwargs)
```

**Aplicado a**: `Area` (módulo `usuarios`).

---

## 3. RelationshipDiffMixin

**Ubicación**: `common/utils/mixins/relationships.py`

**Propósito**: Maneja diferencias (diff) en relaciones ManyToMany. Permite especificar qué IDs agregar (`add`) y cuáles quitar (`remove`) en una sola operación.

**Problema que resuelve**: Django no tiene forma nativa de hacer "sync" de M2M donde se especifican adiciones y eliminaciones en un solo paso. Este mixin procesa el diff y aplica los cambios.

**API esperada**:
```python
{
    "add": [id1, id2],
    "remove": [id3]
}
```

**Características**:
- Soporta **intermediate tables manuales** (con modelo intermedio explícito).
- Previene duplicados en adiciones (usiando `bulk_create` con dedup).
- Soporta Django M2M estándar.

**Uso típico**: ViewSets que manejan asignación de permisos, roles o grupos a entidades.

---

## 4. JsonPayloadMixin

**Ubicación**: `common/utils/mixins/payload.py`

**Propósito**: Permite que un serializer procese peticiones `multipart/form-data` donde el payload principal va en un campo `data` (JSON string), y los archivos van como campos separados (`file_<UUID>`).

**Problema que resuelve**: Cuando se sube archivos con datos complejos, el frontend envía el JSON como string en el campo `data` y los archivos binarios como `file_<uuid>`. El mixin:
1. Extrae el JSON del campo `data`
2. Valida que las claves de archivos cumplan el patrón `file_<UUID de 36 caracteres>`
3. Reemplaza las referencias string `"file_..."` en el JSON por los objetos `UploadedFile` reales

**Patrón de clave de archivo**:
```python
FILE_KEY_PATTERN = re.compile(r'^file_[0-9a-f-]{36}$')
```

**Validación de seguridad**: Si llega una clave que no es `data` ni `file_<uuid>`, lanza `ValidationError` con `security_error`.

**Hidratación recursiva**: El proceso de reemplazo de strings por archivos es recursivo, funcionando en arrays y objetos anidados.

---

## 5. AnexosMixin

**Ubicación**: `common/utils/mixins/anexos.py`

**Propósito**: Procesa operaciones CRUD de anexos (archivos adjuntos) de forma genérica para cualquier modelo que tenga una relación hijo de anexos.

**Acciones soportadas**: `create`, `update`, `delete`

**Configuración requerida** en el serializer que lo usa:
```python
class MiSerializer(AnexosMixin, serializers.ModelSerializer):
    child_model = MiAnexoModel  # Modelo hijo (Anexo)
    fk_field = "campo_fk"        # Nombre del campo FK al padre
```

**Validaciones importantes**:
- Usa `AnexoActionSchema` (Pydantic) para validar cada item.
- **Create**: Requiere archivo binario. Si llega un string, lanza error (protección contra placeholders sin hidratar).
- **Delete/Update**: Requiere `id`.
- **Update**: El archivo es opcional (si no viene, conserva el anterior).

**Errores**: Acumula errores por índice y los lanza todos juntos con `ValidationError`.

---

## 6. AnexoActionSchema (Pydantic)

**Ubicación**: `common/utils/schemas/anexos.py`

**Propósito**: Schema de validación para acciones de anexos. Define la estructura que cada item de anexo debe tener.

**Campos**:
```python
class AnexoActionSchema(BaseModel):
    action: Literal['create', 'update', 'delete']
    id: Optional[str] = None
    descripcion: str = Field(min_length=1, strip_whitespace=True)
```

**Validador personalizado**: `id` es obligatorio para `update` y `delete`, pero opcional para `create`.

---

## 7. SafeFieldCheckMixin

**Ubicación**: `common/utils/permissions.py`

**Propósito**: Limpia `request.data` de artefactos de archivos (`request.FILES`) y valida que solo se envíen campos permitidos.

**Métodos**:
- `get_clean_data_keys(request)`: Retorna las claves de `request.data` excluyendo las que vienen de `request.FILES`.
- `validate_allowed_fields(request, allowed_fields)`: Lanza `PermissionDenied` si se envían campos no autorizados.

**Casos de uso**: ViewSets que reciben datos de formularios con archivos adjuntos y necesitan validar campos específicos sin que los campos de archivos interfieran.

---

## Herencia y Dependencias entre Apps

```
┌─────────────────────────────────────────────────────────────────────┐
│                     common/utils/mixins                              │
├───────────────┬───────────────┬───────────────┬─────────────────────┤
│ sanitization  │ relationships  │   payload     │      anexos          │
│  .py         │   .py         │   .py         │      .py              │
│               │               │               │                      │
│ - Sanitize    │ - Relationship│ - JsonPayload │ - AnexosMixin        │
│   EmptyString │   DiffMixin   │   Mixin       │                      │
│ - Sanitize    │               │               │                      │
│   ModelMixin  │               │               │                      │
└───────┬───────┴───────────────┴───────────────┴──────────────────────┘
        │                                    │
        ▼                                    ▼
┌───────────────┐                  ┌─────────────────┐
│  usuarios    │                  │  schemas/       │
│               │                  │  anexos.py      │
│ Models:       │                  │  (Pydantic)     │
│ - Area        │                  │                  │
│               │                  │                  │
│ Serializers:  │                  │                  │
│ - AreaSer.    │                  │                  │
└───────────────┘                  └─────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────┐
│                 Backend apps                           │
├───────────────────────────────────────────────────────┤
│                                                        │
│  solicitudes/  ──► Usa AnexosMixin para sus anexos    │
│  expedientes/  ──► Usa AnexosMixin para sus anexos   │
│                                                        │
│  todas las apps pueden usar:                           │
│  - JsonPayloadMixin (con archivos en表单)              │
│  - RelationshipDiffMixin (M2M diffs)                  │
│  - SafeFieldCheckMixin (validación de campos)         │
│                                                        │
└───────────────────────────────────────────────────────┘
```

---

## Resumen de Mixins

| Mixin | Tipo |作用于 | Problema que resuelve |
|-------|------|-------|---------------------|
| `SanitizeEmptyStringMixin` | Serializer | Serializers | Normaliza `""` → `None` |
| `SanitizeModelMixin` | Model | Models | Normaliza `""` → `None` en save |
| `RelationshipDiffMixin` | Utility | M2M relations | Diff adición/eliminación en un paso |
| `JsonPayloadMixin` | Serializer | FormData + JSON + archivos | Hidrata referencias de archivos en JSON |
| `AnexosMixin` | Serializer | Anexos/adjuntos | CRUD genérico de archivos adjuntos |
| `SafeFieldCheckMixin` | Permission | Request data | Limpia artefactos de archivos, valida campos |
| `AnexoActionSchema` | Pydantic | Validation | Schema de validación para acciones de anexo |

---

## Notas de Implementación

1. **`SanitizeModelMixin` itera todos los campos del modelo** en cada `save()`. En modelos con muchas字段, considerar cachear la lista de campos filtrados.

2. **`JsonPayloadMixin` requiere que el frontend** envíe las claves de archivo como `file_<UUID de 36 caracteres>`. Cualquier otro formato es rechazado como error de seguridad.

3. **`AnexosMixin` espera que el serializer defina** `child_model` y `fk_field`. Sin estos, lanza `ValueError`.

4. **Los 5 mixins son ortogonales** (no dependen unos de otros) y pueden combinarse en cualquier serializer.
