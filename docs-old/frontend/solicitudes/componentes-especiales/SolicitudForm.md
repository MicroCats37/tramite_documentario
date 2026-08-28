# SolicitudForm

## Overview

`SolicitudForm` is the main form component for creating and editing `Solicitud` entities. It wraps `GenericForm` with domain-specific logic for permissions, field blocking, and delta calculations for related entities.

**File:** `src/app/dashboard/solicitudes/_components/forms/SolicitudForm.tsx`

---

## Architecture

### Form Modes

The component operates in two modes detected by the presence of a `solicitud` prop:

| Mode | Trigger | Schema |
|------|---------|--------|
| **Create** | `solicitud` is `undefined` | `SolicitudCreateSchema` |
| **Edit** | `solicitud` is provided | `SolicitudUpdateSchema` |

### Props

```typescript
interface SolicitudFormProps {
  solicitud?: Solicitud | SolicitudCard;          // Existing record for edit mode
  expedienteBase?: { id: string; id_publico: string } | null; // Base expediente for new records
  currentUser: LoginUserData;                     // Auth context
  onSave: (payload: any) => Promise<void>;       // Submission handler
  onCancel: () => void;                          // Cancel callback
  isLoading?: boolean;                           // Submission loading state
}
```

---

## Permission System (`getFormPermissions`)

### How It Works

Permissions are derived at render time based on the user's role and the form action:

```typescript
const { isEditing, permissions } = useMemo(() => {
  const editing = !!solicitud;
  const formAction = editing ? "SolicitudActualizar" : "SolicitudCrear";
  const perms = getFormPermissions(currentUser.rol, formAction as any);
  return { isEditing: editing, permissions: perms };
}, [solicitud, currentUser.rol]);
```

### Permission Flags

The `getFormPermissions` function returns an object with boolean flags that control which fields the current user can modify:

| Flag | Controls |
|------|----------|
| `canEditEstado` | `estado` field |
| `canEditFinalizado` | `finalizado` field |
| `canEditUsuarioAsignado` | `usuario_asignado` field |
| `canEditAreaResponsable` | `area_responsable` field |
| `canEditUsuariosAdjuntados` | `usuarios_adjuntados` field |
| `canEditEvidencia` | `anexos` field |

### Field Blocking Logic

Fields are disabled at the UI level based on permissions **and** an additional lock state:

```typescript
const isFinalizadoAndLocked = isEditing && solicitud?.finalizado === true && !currentUser.is_superuser;
```

This means:
- If a `Solicitud` is marked as `finalizado: true`
- AND the user is **not** a superuser
- **All fields** are locked regardless of individual permissions

The `disabled` prop passed to each SmartSelect combines both:

```typescript
disabled={!permissions.canEditEstado || isFinalizadoAndLocked}
```

---

## Field Dependency Graph

```
expediente (read-only, always)
         │
         ▼
area_responsable ─────────────────┐
         │                        │
         ▼                        ▼
usuario_asignado         usuarios_adjuntados
                                 │
                                 ▼
                              anexos
```

---

## SmartSelect Integration

Each SmartSelect is registered as a `customField` in `GenericForm`:

| Field | SmartSelect Component | Dependency |
|-------|----------------------|-----------|
| `estado` | `SmartEstadoSelect` | Reads `area_responsable` from form |
| `area_responsable` | `SmartAreaSelect` | Clears `usuario_asignado` on change |
| `usuario_asignado` | `SmartUserSelect` | Reverse-syncs `area_responsable` |
| `usuarios_adjuntados` | `SmartCollaboratorsSelect` | None |
| `anexos` | `AnexosManager` | Locked by `isFinalizadoAndLocked` |

---

## Delta Logic for `usuarios_adjuntados`

### Why Delta?

`usuarios_adjuntados` is a many-to-many relationship. Sending the full list on every update causes unnecessary database writes and potential race conditions. Instead, the form calculates the **difference** (delta) between the initial state and the current state.

### Create Mode (POST)

```typescript
// In creation, we send { add: [...] } if there are users
if (payloadData.usuarios_adjuntados && payloadData.usuarios_adjuntados.length > 0) {
  payloadData.usuarios_adjuntados = { add: payloadData.usuarios_adjuntados };
} else {
  delete payloadData.usuarios_adjuntados;
}
```

### Edit Mode (PATCH)

```typescript
// Calculate what was added and what was removed
const initialIds = (formDefaultValues as any).usuarios_adjuntados || [];
const currentIds = values.usuarios_adjuntados || [];

const toAdd = currentIds.filter((id: number) => !initialIds.includes(id));
const toRemove = initialIds.filter((id: number) => !currentIds.includes(id));

if (toAdd.length > 0 || toRemove.length > 0) {
  payloadData.usuarios_adjuntados = JSON.stringify({ add: toAdd, remove: toRemove });
} else {
  delete payloadData.usuarios_adjuntados; // No changes, don't touch the relationship
}
```

### Payload Structure

The backend receives a delta object:

```json
{
  "usuarios_adjuntados": {
    "add": [3, 5],
    "remove": [8]
  }
}
```

This is processed by `RelationshipDiffMixin` on the backend to apply only the necessary changes.

---

## Payload Cleaning (Security)

Before submission, the `handleSubmit` function **removes** any field the user cannot edit:

```typescript
// Example: User cannot edit estado → delete it from payload
if (!permissions.canEditEstado) delete payloadData.estado;
```

This ensures the API never receives fields the user isn't permitted to modify, preventing privilege escalation.

---

## Validation

### Manual Business Validation

Before submit, a mirror of backend validation runs client-side:

```typescript
if (values.finalizado === true) {
  const anexosActivos = (values.anexos || []).filter(a => a.action !== 'delete').length;
  const errorFinalizacion = solicitudValidations.finalizado(true, anexosActivos);
  if (errorFinalizacion) {
    toast.error(errorFinalizacion);
    return; // Block submit
  }
}
```

This prevents the user from finalizing a `Solicitud` without required evidence.

---

## State Management

### `liveUser` State

A local `useState` tracks the currently selected user for `SmartEstadoSelect`:

```typescript
const [liveUser, setLiveUser] = useState<any>(null);
```

This allows the estado selector to react to user changes without waiting for form submission.

---

## Related Files

| File | Role |
|------|------|
| `SmartEstadoSelect.tsx` | Estado selector with role-based filtering |
| `SmartUserSelect.tsx` | User selector with reverse area sync |
| `SmartAreaSelect.tsx` | Area selector with ID<->Slug conversion |
| `SmartCollaboratorsSelect.tsx` | Multi-user selector with delta tracking |
| `GenericForm.tsx` | Base form wrapper |
| `useSolicitudUI.ts` | Dynamic form section definitions |
| `getFormPermissions` | Permission matrix function |
| `solicitudValidations` | Client-side business rules |
