# UbigeoSmartSet

**Archivo**: `frontend/src/app/dashboard/expedientes/_components/forms/UbigeoSmartSet.tsx`

**Propósito**: Selector encadenado de tres niveles (Departamento → Provincia → Distrito) que toma los datos de ubigeo desde `@/lib/data/ubigeo`. **Actualmente no está integrado en el formulario de expedientes.**

---

## 1. Estado Actual

Este componente **no se usa** en `ExpedienteForm` ni en ninguna parte del flujo de creación/edición de expedientes. La razón más probable es que el schema Zod (`ExpedienteCreateSchema` / `ExpedienteUpdateSchema`) **no incluye los campos** `departamento`, `provincia` ni `distrito`.

Revisando `form.ts` del módulo validations/expedientes:

```typescript
const ExpedienteBaseFields = {
  tipo_persona: z.string().default("NATURAL"),
  dni: z.string().nullable().default(""),
  // ... teléfono, correo, tipo_documento, numero_documento, asunto, observaciones
  // NO hay: departamento, provincia, distrito
};
```

El schema carece de estos tres campos, por lo que integrarlo requeriría primero agregarlos al schema Zod.

---

## 2. Arquitectura del Componente

```
UbigeoSmartSet<T>
├── useEffect (edit mode) → carga listas según valores actuales
├── watch("departamento") → reacciona a cambios
├── handleDepartamentoChange → limpia provincia y distrito, carga nuevas provincias
├── handleProvinciaChange → limpia distrito, carga nuevos distritos
└── handleDistritoChange → solo setValue
```

Usa `useController` via `FormField` de `react-hook-form` para cada selector. El casting `as Path<T>` es necesario porque los nombres de campo (`"departamento"`, `"provincia"`, `"distrito"`) son strings literales que no existen en el tipo genérico `T`.

---

## 3. Datos de Ubigeo

Los datos se importan de `@/lib/data/ubigeo`:

```typescript
import { getDepartamentos, getProvincias, getDistritos } from "@/lib/data/ubigeo";
```

- `getDepartamentos()` → `string[]`
- `getProvincias(departamento)` → `string[]`
- `getDistritos(departamento, provincia)` → `string[]`

Estos datos son estáticos (hardcoded o JSON embebido), no hay llamadas a API para obtenerlos.

---

## 4. Flujo de Cascada

```
Usuario selecciona DEPARTAMENTO
  → setValue("departamento", value, { shouldValidate: true })
  → setValue("provincia", "")       // Limpia hijo
  → setValue("distrito", "")        // Limpia nieto
  → setProvincias(getProvincias(value))

Usuario selecciona PROVINCIA
  → setValue("provincia", value, { shouldValidate: true })
  → setValue("distrito", "")        // Limpia nieto
  → setDistritos(getDistritos(dept, value))

Usuario selecciona DISTRITO
  → setValue("distrito", value, { shouldValidate: true })
```

`shouldValidate: true` hace que Zod re-evalúe el campo inmediatamente, mostrando el error rojo (`FormMessage`) si el campo queda vacío cuando es requerido.

---

## 5. Validación de Errores

```typescript
<SelectTrigger className={form.formState.errors[fieldDept] ? "border-red-500" : ""}>
```

Aplica `border-red-500` manualmente al `SelectTrigger` cuando hay error en ese campo. Esto es un workaround porque `FormField` de shadcn/ui no propaga el error al `SelectTrigger` automáticamente.

`FormMessage` se coloca después del `Select` y muestra el mensaje de error de Zod.

---

## 6. Efecto Inicial (Edit Mode)

```typescript
useEffect(() => {
  const dept = getValues(fieldDept);
  const prov = getValues(fieldProv);
  if (dept) setProvincias(getProvincias(dept));
  if (dept && prov) setDistritos(getDistritos(dept, prov));
}, []);
```

Cuando el form ya tiene valores (edición de un expediente existente), el efecto carga las listas de provincia y distrito correspondientes a los valores guardados. Sin este efecto, los selects estarían vacíos al recargar la página.

---

## 7. Props

| Prop | Tipo | Descripción |
|---|---|---|
| `form` | `UseFormReturn<T>` | Instancia del form completo |

**Interfaz genérica**: `UbigeoSmartSetProps<T extends FieldValues>` — es reutilizable en cualquier form que tenga campos `departamento`, `provincia`, `distrito`.

---

## 8. Próximos Pasos si se Integrara

1. Agregar `departamento`, `provincia`, `distrito` a `ExpedienteBaseFields` en `validations/expedientes/form.ts`
2. Agregar `<UbigeoSmartSet form={methods} />` a `customFields` en `ExpedienteForm.tsx`
3. Silenciar los campos originales en `customFields` con `() => null` (igual que se hace con `dni`, `ruc`, etc.)
4. Opcionalmente agregarlos a `expedienteUI` en la sección correspondiente
