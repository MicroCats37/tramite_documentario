# SmartUserSelect

## Overview

`SmartUserSelect` is a smart selector that automatically filters users by the selected area and supports **reverse synchronization** — when a user is selected, it auto-fills the area field.

**File:** `src/app/dashboard/solicitudes/_components/forms/SmartUserSelect.tsx`

---

## API Consumption

### Data Sources

| Hook | Endpoint | Purpose |
|------|----------|---------|
| `useFetchUsuarios` | `GET /usuarios/` | All users (for display names and fallback) |
| `useFetchUsuariosPorArea` | `GET /usuarios/?area={slug}` | Users filtered by area slug |

### Fetch Strategy

```typescript
// When area is selected → fetch filtered users by area slug
const { data: usersByAreaResponse, isLoading: loadingAreaUsers } = useFetchUsuariosPorArea(currentAreaSlug);

// Always fetch ALL users → needed for reverse sync and name resolution
const { data: allUsuariosResponse, isLoading: loadingAllUsers } = useFetchAllUsuarios();
```

**Key insight:** Both fetches run simultaneously. The filtered list is used for display, but the full list is kept in memory for:
1. Resolving user display names even when filtered
2. Reverse sync to detect the user's area

### Data Structure Expected

```typescript
// allUsuariosResponse.results[]
{
  user: { id: number, first_name: string, last_name: string, username: string },
  area: { id: number, slug: string, nombre: string }
}
// OR flat structure
{ id: number, first_name: string, last_name: string, area: { ... } }
```

---

## Filtering Logic

```typescript
const filteredUsers = useMemo(() => {
  if (currentAreaSlug && usersByAreaResponse) {
    return usersByAreaResponse.results || [];
  }
  return allUsuarios;
}, [currentAreaSlug, usersByAreaResponse, allUsuarios]);
```

| `currentAreaSlug` | Shows |
|-------------------|-------|
| `null` / empty | All users |
| `"logistica"` | Only users from logistica area |

---

## React Hook Form Integration

### Controller Pattern

```typescript
const { field } = useController({ name, control });
```

This connects the select to the form's `control` object, enabling:
- Form state integration (validation, errors)
- Value synchronization with other fields
- `disabled` prop propagation

### Value Handling

```typescript
<Select
  value={field.value ? String(field.value) : "unassigned"}
  onValueChange={(val) => {
    const userId = val === "unassigned" ? null : Number(val);
    field.onChange(userId);
    // ... reverse sync logic
  }}
  disabled={disabled}
/>
```

- `field.value` is a number (`user.id`)
- `"unassigned"` is the UI sentinel for `null`
- Conversion: `Number(val)` when selecting, `String(field.value)` when displaying

---

## Reverse Synchronization

When a user is selected, the component automatically updates the `area_responsable` field:

```typescript
if (userId && nameArea && areasList) {
  // Find user in ALL users list to get their area
  const userInGlobal = allUsuarios.find((u: any) => {
    const uId = u.user?.id || u.id;
    return Number(uId) === userId;
  });

  const userAreaSlug = (userInGlobal as any)?.area?.slug;
  if (userAreaSlug) {
    const areaFound = areasList.find(a => a.slug === userAreaSlug);
    if (areaFound && Number(areaFound.id) !== Number(currentAreaId)) {
      setValue(nameArea, areaFound.id, { shouldValidate: true });
    }
  }
}
```

**Flow:** User selects "John Doe" → Component finds John's area is "Logística" → Sets `area_responsable` to Logísticas's ID.

---

## Props

```typescript
interface SmartUserSelectProps {
  name: string;              // RHF field name (e.g., "usuario_asignado")
  nameArea?: string;         // Area field name for reverse sync (e.g., "area_responsable")
  label?: string;            // Display label (default: "Usuario Asignado")
  disabled?: boolean;        // Disable the control
}
```

---

## Display Text Resolution

The select trigger shows contextual information:

```typescript
const getDisplayText = () => {
  if (!currentUserId || currentUserId === "unassigned") {
    return !currentAreaId ? "Buscar (Todos)..." : "Seleccionar colaborador...";
  }

  // Find user in ALL list to get area name
  const selectedUser = allUsuarios.find((u) => Number(u.user?.id || u.id) === Number(currentUserId));
  const userObj = selectedUser.user || selectedUser;
  const areaName = selectedUser.area?.nombre;

  if (!currentAreaId && areaName) {
    return `${userObj.first_name} ${userObj.last_name} (${areaName})`;
  }
  return `${userObj.first_name} ${userObj.last_name}`;
};
```

Shows `John Doe (Logística)` when no area filter is active, or just `John Doe` when filtered by area.

---

## Related Files

| File | Role |
|------|------|
| `useFetchUsuarios` | Service hook for all users |
| `useFetchUsuariosPorArea` | Service hook for area-filtered users |
| `useFetchAreas` | For slug→ID resolution in reverse sync |
| `AreaSelect` | Base component |
