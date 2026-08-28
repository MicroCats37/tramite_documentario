# ExpedienteForm

**Archivo**: `frontend/src/app/dashboard/expedientes/_components/forms/ExpedienteForm.tsx`

**Propósito**: Formulario principal para crear y editar expedientes. orquestra dos esquemas Zod diferenciados (create vs. update), delega el renderizado de secciones dinámicas a componentes hijos, y construye el payload final que recibe `onSave`.

---

## 1. Arquitectura General

```
ExpedienteForm
├── ExpedienteCreateSchema / ExpedienteUpdateSchema  ← Zod
├── GenericForm                                      ← Motor de renderizado
├── DatosSolicitanteSection (customFields)           ← DNI/RUC/CIP dinámic
├── SmartFileField (customFields)                    ← Archivo principal
└── AnexosManager (customFields)                    ← Galería de anexos
```

**Patrón**: Composition over configuration. `GenericForm` recibe un array de `FormSection` (`expedienteUI`) y un mapa de `customFields`. Los campos que no tienen custom renderer se renderizan automáticamente con los componentes estándar (Input, Select, Textarea).

---

## 2. Selección de Esquema Zod

```typescript
const currentSchema = isEditing ? ExpedienteUpdateSchema : ExpedienteCreateSchema;
```

| Esquema | `archivo_principal` | Requerido |
|---|---|---|
| `ExpedienteCreateSchema` | `z.union([z.instanceof(File), z.null()])` + `.refine()` | **Sí** — falla si es `null` |
| `ExpedienteUpdateSchema` | `z.union([z.instanceof(File), z.string(), z.null()]).optional().nullable()` | **No** |

La distinción es crítica: en creación el archivo es obligatorio; en edición es opcional porque ya existe uno en el backend.

---

## 3. Valores Iniciales (模式切换)

### Creación (`isEditing = false`)

```typescript
const createData: ExpedienteCreateFormData = {
  tipo_persona: "NATURAL",
  archivo_principal: null,   // Zod falla si no se sube archivo
  anexos: [],
  // ... todos los strings vacíos o ""
};
```

### Edición (`isEditing = true`)

```typescript
const updateData: ExpedienteUpdateFormData = {
  // Mapeo backend → frontend (nombres de campo idénticos)
  archivo_principal: expediente.archivo_principal || undefined, // String (URL del backend)
  anexos: expediente.anexos?.map((a) => ({
    id: a.id,
    descripcion: a.descripcion,
    file: a.archivo_anexo, // URL del anexo existente
    action: "none"
  })),
};
```

**Nota de casting**: `telefono`, `correo`, `tipo_documento`, `observaciones` usan casting `(expediente as any)` porque el schema `ExpedienteSchema` del backend no los incluye como required, pero el schema de formulario sí los necesita.

---

## 4. customFields — Desactivación de Renderizado Automático

Los campos `dni`, `ruc`, `razon_social`, `nombres`, `apellidos`, `telefono`, `correo`, `cip` se silencian con `() => null` en `customFields`. Esto es **necesario** porque `DatosSolicitanteSection` los renderiza manualmente dentro de su propia grid de 12 columnas. Si no se silencian, `GenericForm` intentaría renderizarlos dos veces.

```typescript
dni: () => null,
ruc: () => null,
// ... etc
```

---

## 5. Submit Handler y Payload Building

```typescript
const handleSubmit: SubmitHandler<ExpedienteFormValues> = async (values) => {
  const payloadData: any = { ...values };

  // Anexos: prepareAnexosPayload transforma la galería en acciones create/delete/none
  if (values.anexos) {
    payloadData.anexos = prepareAnexosPayload(values.anexos);
  }

  // Si archivo_principal ya existe en backend (string/URL), se elimina del payload
  // para no enviar una URL como si fuera un File
  if (typeof payloadData.archivo_principal === 'string') {
    delete payloadData.archivo_principal;
  }

  const finalPayload = buildApiPayload(payloadData);
  await onSave(finalPayload);
};
```

**Flujo del payload**:
1. `values` → datos crudos del formulario (puede contener `File`, `string` o `null`)
2. `prepareAnexosPayload` → convierte cada anexo en `{ id, action: 'create'|'delete'|'none', file?, descripcion }`
3. Si `archivo_principal` es `string` (URL existente del backend) → se elimina del objeto; el backend conserva el archivo actual
4. `buildApiPayload` → utilidad de root que puede serializar `FormData` si el endpoint lo requiere

---

## 6. Props

| Prop | Tipo | Descripción |
|---|---|---|
| `expediente` | `Expediente \| null` | Si está presente, modo edición; si `null`/`undefined`, modo creación |
| `onSave` | `(payload) => Promise<void>` | Callback que recibe el payload ya construido |
| `onCancel` | `() => void` | Navega de vuelta |
| `isLoading` | `boolean` | Deshabilita el submit mientras persiste |

---

## 7. Dependencias de Validación

El formulario **no valida intercampos cross-section** (e.g., no exige que si `tipo_persona === 'NATURAL'` entonces `dni` tenga exactamente 8 dígitos). Eso queda fuera del alcance del schema Zod y es responsabilidad del consumidor o de una capa de validación adicional.
