# SmartAssignmentSelect

## Overview

`SmartAssignmentSelect` is a compound component that combines area and user selection in a single UI block with bidirectional synchronization. It allows assigning both the responsible area and the responsible user together.

**File:** `src/app/dashboard/solicitudes/_components/forms/SmartAssignmentSelect.tsx`

---

## Architecture

This component is distinct from the other SmartSelect components because it **manages two fields simultaneously** rather than wrapping a single field. It's designed as a self-contained assignment widget.

### Data Flow

```
┌─────────────────────────────────────────────────────────┐
│  SmartAssignmentSelect                                   │
│                                                         │
│  ┌─────────────────┐    ┌─────────────────────────┐   │
│  │  AreaSelect     │───▶│  Updates nameArea field │   │
│  │  (Slug-based)   │    └─────────────────────────┘   │
│  └─────────────────┘                                    │
│         │                         │                    │
│         ▼                         ▼                    │
│  ┌─────────────────┐    ┌─────────────────────────┐   │
│  │  Filter Users   │    │  Updates nameUsuario    │   │
│  │  by Area ID     │    │  field + reverse sync   │   │
│  └─────────────────┘    └─────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## API Consumption

### Data Sources

| Hook | Endpoint | Purpose |
|------|----------|---------|
| `useFetchAreas` | `GET /areas/` | Area list for slug→ID mapping |
| `useFetchUsuarios` | `GET /usuarios/` | All users for filtering |

```typescript
const { data: areasList } = useFetchAreas();
const { data: allUsuariosResponse } = useFetchAllUsuarios();
const allUsuarios = allUsuariosResponse?.results || [];
```

---

## User Filtering

```typescript
const filteredUsers = useMemo(() => {
  if (!allUsuarios.length) return [];
  if (!currentAreaId) return allUsuarios;  // No filter → show all

  return allUsuarios.filter((u: any) => {
    const areaObj = u.area || u.perfilusuario?.area;
    const userAreaId = areaObj?.id;
    return userAreaId === currentAreaId;
  });
}, [allUsuarios, currentAreaId]);
```

When an area is selected, only users belonging to that area are shown.

---

## Bidirectional Synchronization

### Area → User

When the area changes, the user field is cleared:

```typescript
const handleAreaChange = (slug: string) => {
  if (!slug) {
    setValue(nameArea, null, { shouldValidate: true });
    return;
  }

  const areaObj = areasList?.find(a => a.slug === slug);
  if (areaObj?.id) {
    setValue(nameArea, areaObj.id, { shouldValidate: true });

    // Clear user if area changed
    if (currentUserId) {
      setValue(nameUsuario, null);
    }
  }
};
```

### User → Area (Reverse Sync)

When a user is selected, their area is automatically selected:

```typescript
onValueChange={(val) => {
  const userId = val === "unassigned" ? null : Number(val);
  field.onChange(userId);

  if (userId) {
    const selectedUser = allUsuarios.find((u) => {
      const uId = u.user?.id || u.id;
      return uId === userId;
    });

    const areaSlug = (selectedUser as any)?.area?.slug;
    if (areaSlug && areasList) {
      const areaFound = areasList.find(a => a.slug === areaSlug);
      if (areaFound && areaFound.id !== currentAreaId) {
        setValue(nameArea, areaFound.id, { shouldValidate: true });
      }
    }
  }
}}
```

---

## React Hook Form Integration

Uses `Controller` for the user field (same pattern as other SmartSelects) and direct `watch`/`setValue` for the area field:

```typescript
const { control, watch, setValue, formState: { errors } } = useFormContext();

const currentAreaId = watch(nameArea);      // Watch area field
const currentUserId = watch(nameUsuario);    // Watch user field

<Controller
  control={control}
  name={nameUsuario}
  render={({ field }) => (
    <Select value={field.value ? String(field.value) : "unassigned"} ...>
    </Select>
  )}
/>
```

---

## Props

```typescript
interface SmartAssignmentSelectProps {
  nameArea: string;    // Form field name for area (e.g., "area_responsable")
  nameUsuario: string; // Form field name for user (e.g., "usuario_asignado")
  disabled?: boolean;
}
```

---

## Informational Message

When an area is selected but no user is assigned:

```typescript
{currentAreaId && !currentUserId && (
  <div className="text-[10px] text-amber-600 mt-1 flex items-center gap-1">
    ⚠️ La solicitud será asignada a la bandeja general del Área.
  </div>
)}
```

This informs the user that leaving the user field empty means the solicitud goes to the area's general inbox.

---

## Relationship with Other SmartSelects

In `SolicitudForm`, the individual selectors are used separately (`SmartAreaSelect` + `SmartUserSelect`) rather than this combined component. `SmartAssignmentSelect` appears to be an alternative/combined pattern that exists separately.

---

## Related Files

| File | Role |
|------|------|
| `AreaSelect` | Base component for area dropdown |
| `useFetchAreas` | Areas data |
| `useFetchUsuarios` | Users data |
