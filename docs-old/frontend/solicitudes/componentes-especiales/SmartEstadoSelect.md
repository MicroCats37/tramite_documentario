# SmartEstadoSelect

## Overview

`SmartEstadoSelect` is a state selector that filters available states based on the user's role using `getEstadosVisiblesPorRol`. It also provides contextual display text for certain states (e.g., showing the area name for "ENVIADO_A_AREA").

**File:** `src/app/dashboard/solicitudes/_components/forms/SmartEstadoSelect.tsx`

---

## API Consumption

### No Direct API Calls

This component does **not** fetch data. Instead, it uses static data functions:

| Function | Source | Purpose |
|----------|--------|---------|
| `getEstadosVisiblesPorRol(rol)` | `@/lib/data/solicitud/estados` | Get role-appropriate states |
| `getEstadoLabel(estado)` | `@/lib/data/solicitud/estados` | Get human-readable labels |

---

## React Hook Form Integration

### Controller Pattern

```typescript
const { field, fieldState: { error } } = useController({ name, control });
```

Unlike `SmartAreaSelect` and `SmartUserSelect`, this component receives `control` as a prop rather than using `useFormContext`:

```typescript
interface SmartEstadoSelectProps {
  control: Control<any>;  // Passed from parent form
  name: string;
  // ...
}
```

This is because `SmartEstadoSelect` is rendered inside `customFields` where the `methods` object (containing `control`) is passed explicitly.

---

## Role-Based Filtering

```typescript
const opcionesDisponibles = useMemo(() => {
  return getEstadosVisiblesPorRol(rol).map((e) => ({
    value: e,
    label: getEstadoLabel(e),
  }));
}, [rol]);
```

Each role sees a different subset of states. If the current `field.value` is not in the available options, it's treated as a read-only state from another role.

---

## Value Override Logic

### Problem

A state that is valid for one role may not be in the list for another role. If a "Funcionario" views a solicitud with `estado: "ARCHIVADO"`, that state won't appear in their dropdown.

### Solution

```typescript
const isValueInOptions = opcionesDisponibles.some(opt => opt.value === field.value);
const shouldOverrideText = !isValueInOptions || (field.value === "ENVIADO_A_AREA" && nombreArea);

const getDisplayText = () => {
  if (!field.value) return "Seleccione un estado";

  if (field.value === "ENVIADO_A_AREA" && nombreArea) {
    return `Enviado a ${nombreArea}`;  // Show area name
  }

  return getEstadoLabel(field.value);
};
```

**Override conditions:**
1. Current value is NOT in the role's available options → Show as read-only
2. State is `ENVIADO_A_AREA` → Show `Enviado a {AreaName}`

### Read-Only Indicator

When viewing a state outside the user's权限:

```typescript
{!isValueInOptions && field.value && (
  <p className="text-[10px] text-amber-600 font-medium">
    * Estado actual (Solo lectura para tu rol)
  </p>
)}
```

---

## Props

```typescript
interface SmartEstadoSelectProps {
  control: Control<any>;
  name: string;
  label?: string;
  disabled?: boolean;
  rol: LoginUserData["rol"];
  usuarioAsignado?: { area?: { nombre: string } } | null;  // For area name in ENVIADO_A_AREA
  areaAsignada?: { nombre: string } | null;                // Preferred source for area name
}
```

---

## Area Name Resolution

The component needs to display the area name when `estado === "ENVIADO_A_AREA"`. It accepts two sources:

```typescript
const nombreArea = areaAsignada?.nombre || usuarioAsignado?.area?.nombre;
```

- `areaAsignada` — Direct prop (preferred, from form state)
- `usuarioAsignado?.area?.nombre` — Fallback from user object

---

## SelectValue Workaround

Radix UI's `SelectValue` requires a valid React element as a child, not plain text:

```typescript
<SelectValue placeholder="Seleccione estado">
  {shouldOverrideText ? (
    <span>{getDisplayText()}</span>
  ) : undefined}
</SelectValue>
```

When `shouldOverrideText` is false, `SelectValue` shows the matched `SelectItem` text normally.

---

## Related Files

| File | Role |
|------|------|
| `@/lib/data/solicitud/estados` | `getEstadosVisiblesPorRol`, `getEstadoLabel` |
| `@/components/ui/select` | Base Radix UI Select components |
