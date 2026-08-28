# SmartAreaSelect

## Overview

`SmartAreaSelect` wraps the base `AreaSelect` component with React Hook Form integration and automatic ID<->Slug conversion. It stores IDs in the form but communicates with `AreaSelect` via slugs.

**File:** `src/app/dashboard/solicitudes/_components/forms/SmartAreaSelect.tsx`

---

## API Consumption

### Data Source

| Hook | Endpoint | Purpose |
|------|----------|---------|
| `useFetchAreas` | `GET /areas/` | Fetch all areas for ID↔Slug mapping |

```typescript
const { data: areasList, isLoading } = useFetchAreas();
```

---

## React Hook Form Integration

### Controller Pattern

```typescript
const { field, fieldState: { error } } = useController({ name, control });
```

- `field.value` — Current area **ID** (number or null)
- `field.onChange` — Accepts area **ID**
- `error` — Validation error from RHF

### ID <-> Slug Conversion

The form stores **ID** but `AreaSelect` works with **slugs**:

```typescript
// ID → Slug (for displaying current value)
const currentSlug = (() => {
  if (!field.value || !areasList) return "";
  const found = areasList.find(a => Number(a.id) === Number(field.value));
  return found ? found.slug : "";
})();

// Slug → ID (when user selects)
const handleAreaChange = (newSlug: string) => {
  if (!newSlug) {
    field.onChange(null);
    return;
  }

  const areaFound = areasList?.find(a => a.slug === newSlug);
  if (areaFound) {
    field.onChange(areaFound.id); // Store ID in form
  }
};
```

**Conversion flow:**
1. User sees slug-based dropdown in `AreaSelect`
2. On selection, component finds matching area and stores its **ID** in the form
3. When displaying, finds area by ID and shows corresponding slug

---

## Cascade Clearing

When the area changes, the dependent user field is cleared:

```typescript
const handleAreaChange = (newSlug: string) => {
  if (!newSlug) {
    field.onChange(null);
    return;
  }

  const areaFound = areasList?.find(a => a.slug === newSlug);
  if (areaFound) {
    field.onChange(areaFound.id);

    // Clear dependent user field
    if (nameUsuarioDependiente) {
      setValue(nameUsuarioDependiente, null);
    }
  }
};
```

This prevents stale user assignments when the area changes.

---

## Props

```typescript
interface SmartAreaSelectProps {
  name: string;                    // RHF field name (e.g., "area_responsable")
  label?: string;                 // Display label
  disabled?: boolean;             // Disable control
  nameUsuarioDependiente?: string; // User field to clear on area change
}
```

---

## Usage in SolicitudForm

```typescript
area_responsable: () => (
  <div className="col-span-12 md:col-span-6">
    <SmartAreaSelect
      name="area_responsable"
      nameUsuarioDependiente="usuario_asignado"
      disabled={!permissions.canEditAreaResponsable || isFinalizadoAndLocked}
    />
  </div>
),
```

---

## Debug Logging

Development-only logs track the conversion process:

```typescript
useEffect(() => {
  if (process.env.NODE_ENV === 'development') {
    console.log(`[SmartAreaSelect:${name}] Value:`, field.value);
    console.log(`[SmartAreaSelect:${name}] Areas available:`, areasList?.length || 0);
  }
}, [field.value, areasList, name]);
```

---

## Related Files

| File | Role |
|------|------|
| `AreaSelect` | Base UI component (slug-based) |
| `useFetchAreas` | Areas data hook |
| `useFormContext` | RHF context |
