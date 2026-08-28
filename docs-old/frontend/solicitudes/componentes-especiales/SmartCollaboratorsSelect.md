# SmartCollaboratorsSelect

## Overview

`SmartCollaboratorsSelect` provides a multi-user selection interface for adding collaborators (`usuarios_adjuntados`) to a Solicitud. It uses a tag-based UI with area filtering and supports delta calculation for efficient API updates.

**File:** `src/app/dashboard/solicitudes/_components/forms/SmartCollaboratorsSelect.tsx`

---

## UI Pattern

```
┌────────────────────────────────────────────────────────────┐
│  Gestión de Colaboradores (Multiselección)                  │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐ │
│  │ [Tag: Juan] [Tag: María] [Tag: Carlos]               │ │
│  │ (click X to remove)                                   │ │
│  └──────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────────────┐  │
│  │ AreaSelect          │  │ Select User → Add          │  │
│  │ (filters user list) │  │ [Disabled if no area]     │  │
│  └─────────────────────┘  └─────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## API Consumption

### Data Sources

| Hook | Endpoint | Purpose |
|------|----------|---------|
| `useFetchUsuariosPorArea` | `GET /usuarios/?area={slug}` | Users filtered by selected area |
| `useFetchUsuarios` | `GET /usuarios/` | All users (for name resolution) |

```typescript
// Users filtered by selected area (for the dropdown)
const { data: usuariosArea, isLoading: isLoadingUsuarios } = useFetchUsuariosPorArea(
  selectedArea || null,  // null when no area selected
);

// All users (for resolving names in tags)
const { data: allUsuarios } = useFetchUsuarios();
```

---

## State Management

### Form State

The selected user IDs are stored directly in the form field as an array:

```typescript
const currentIds: number[] = watch(name) || [];
```

### Local UI State

Area filter is stored locally (not in form) because it's a UI concern, not data:

```typescript
const [selectedArea, setSelectedArea] = useState<string>("");
```

---

## Adding Users

```typescript
const handleAddUser = (userIdStr: string) => {
  const id = Number(userIdStr);
  if (!currentIds.includes(id)) {
    setValue(name, [...currentIds, id], { shouldValidate: true });
  }
};
```

- Converts string to number
- Prevents duplicates
- Updates form field with the new array

---

## Removing Users

```typescript
const handleRemoveUser = (idToRemove: number) => {
  setValue(
    name,
    currentIds.filter((id) => id !== idToRemove),
    { shouldValidate: true },
  );
};
```

Removes the ID from the array.

---

## Name Resolution

Since the dropdown shows users from a filtered list (by area), but tags need to display names even when the filter changes, names are resolved from the **all users** list:

```typescript
const getUserName = (id: number) => {
  const userItem = allUsuarios?.results.find((u) => {
    const uId = u.user?.id;
    return uId === id;
  });
  if (!userItem) return `ID: ${id}`;  // Fallback

  const userObj = userItem.user || userItem;
  return `${userObj.first_name} ${userObj.last_name}`;
};
```

---

## Filtering the Dropdown

Users already selected are excluded from the dropdown:

```typescript
{usuariosArea?.results
  .filter((u) => {
    const uid = u.user?.id;
    return !currentIds.includes(uid);  // Don't show already-selected users
  })
  .map((u: any) => {
    const userObj = u.user || u;
    const uid = userObj.id || u.id;
    return (
      <SelectItem key={uid} value={String(uid)}>
        {userObj.first_name} {userObj.last_name}
      </SelectItem>
    );
  })}
```

---

## React Hook Form Integration

Unlike other SmartSelects, this component uses `useFormContext` directly (not `useController`) and manages an array:

```typescript
const { watch, setValue } = useFormContext();
const currentIds: number[] = watch(name) || [];
```

The `name` prop allows the component to work with any array field.

---

## Props

```typescript
interface SmartCollaboratorsSelectProps {
  name: string;      // RHF field name for the user ID array
  label?: string;    // Display label
  disabled?: boolean;
}
```

---

## Disable Logic

The user dropdown is disabled when:
1. No area is selected (`!selectedArea`)
2. Users are loading (`isLoadingUsuarios`)
3. The entire component is disabled (`disabled`)

```typescript
disabled={disabled || !selectedArea || isLoadingUsuarios}
```

The add button inside the Select is disabled until an area is chosen.

---

## Usage in SolicitudForm

```typescript
usuarios_adjuntados: () => (
  <div className="col-span-12">
    <SmartCollaboratorsSelect
      name="usuarios_adjuntados"
      label="Usuarios Adjuntados"
      disabled={!permissions.canEditUsuariosAdjuntados || isFinalizadoAndLocked}
    />
  </div>
),
```

---

## Delta Calculation (Handled by SolicitudForm)

The actual delta calculation (`{ add: [...], remove: [...] }`) happens in `SolicitudForm.handleSubmit`, not in this component. This component only manages the array of selected IDs.

---

## Related Files

| File | Role |
|------|------|
| `AreaSelect` | Base component for area filtering |
| `useFetchUsuarios` | All users for name resolution |
| `useFetchUsuariosPorArea` | Area-filtered users for dropdown |
| `@/components/ui/badge` | Tag display |
