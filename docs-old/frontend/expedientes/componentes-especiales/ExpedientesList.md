# ExpedientesList

**Responsabilidad**: Componente de presentación que recibe una lista de expedientes y los renderiza como cards. Gestiona localmente el modal de vista (`ExpedienteViewModal`) y la paginación. No tiene acceso al estado global ni a mutations.

**Ubicación**: `frontend/src/app/dashboard/expedientes/_components/ExpedientesList.tsx`

---

## Props

```typescript
interface ExpedientesListProps {
  user: LoginUserData;
  expedientes: Expediente[];
  isLoading: boolean;
  onEditExpediente: (expediente: Expediente) => void;
  onEditSolicitud: (expediente: Expediente) => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}
```

### Props detalladas

| Prop | Tipo | Descripción |
|------|------|-------------|
| `user` | `LoginUserData` | Usuario actual (para comparar con asignado en cards) |
| `expedientes` | `Expediente[]` | Lista de expedientes a mostrar |
| `isLoading` | `boolean` | Flag de loading para mostrar esqueleto |
| `onEditExpediente` | `function` | Callback al padre para editar expediente |
| `onEditSolicitud` | `function` | Callback al padre para editar/crear solicitud |
| `currentPage` | `number` | Página actual |
| `totalPages` | `number` | Total de páginas |
| `onPageChange` | `function` | Callback para cambiar de página |

---

## Estado Local

```typescript
const [showViewModal, setShowViewModal] = useState(false);
const [selectedExpedienteForView, setSelectedExpedienteForView] = useState<Expediente | null>(null);
```

### Uso del estado local

| Estado | Modificado por | Consumido por |
|--------|----------------|---------------|
| `showViewModal` | `handleView`, `ExpedienteViewModal.onClose` | `ExpedienteViewModal.isOpen` |
| `selectedExpedienteForView` | `handleView`, `ExpedienteViewModal.onClose` | `ExpedienteViewModal.expediente` |

---

## Handlers

### `handleView(expediente: Expediente)`
```typescript
const handleView = (expediente: Expediente) => {
  setSelectedExpedienteForView(expediente);
  setShowViewModal(true);
};
```
Abre el modal de vista con el expediente seleccionado.

---

## Estructura de Renderizado

### Loading State
```tsx
{isLoading && (
  <Card className="p-12 text-center">
    <Loader2 className="w-12 h-12 text-primary mx-auto mb-3 animate-spin" />
    <p className="text-muted-foreground">Cargando expedientes...</p>
  </Card>
)}
```

### Empty State
```tsx
{expedientes.length === 0 && (
  <Card className="p-12 text-center">
    <FileText className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
    <p className="text-muted-foreground">No se encontraron expedientes.</p>
  </Card>
)}
```

### Lista de Cards
```tsx
<div className="flex-col w-full space-y-4">
  {expedientes.map((exp) => (
    <ExpedienteCard
      user={user}
      key={exp.id}
      expediente={exp}
      onView={handleView}
      onEditSolicitud={onEditSolicitud}
      onEditExpediente={onEditExpediente}
    />
  ))}
</div>
```

### Paginación
```tsx
{totalPages > 1 && (
  <Pagination>
    {/* Previous / Page numbers / Next */}
  </Pagination>
)}
```

### Modal de Vista
```tsx
<ExpedienteViewModal
  isOpen={showViewModal}
  expediente={selectedExpedienteForView}
  onClose={() => {
    setShowViewModal(false);
    setSelectedExpedienteForView(null);
  }}
/>
```

---

## Algoritmo de Números de Página

```typescript
const getPageNumbers = () => {
  const pages: (number | "ellipsis")[] = [];
  if (totalPages <= 7) {
    // Muestra todas: [1, 2, 3, 4, 5, 6, 7]
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    // Siempre muestra primero, último, y 2-3 alrededor del actual
    pages.push(1);
    if (currentPage > 3) pages.push("ellipsis");
    const start = Math.max(2, currentPage - 1);
    const end = Math.min(totalPages - 1, currentPage + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    if (currentPage < totalPages - 2) pages.push("ellipsis");
    pages.push(totalPages);
  }
  return pages;
};
```

---

## Componentes Hijos

| Componente | Props | Propósito |
|------------|-------|----------|
| `ExpedienteCard` | `user`, `expediente`, `onView`, `onEditExpediente`, `onEditSolicitud` | Card individual |
| `ExpedienteViewModal` | `isOpen`, `expediente`, `onClose` | Modal de solo lectura |

---

## Notas de Implementación

- **Sin mutations**: `ExpedientesList` no ejecuta create/update/delete — solo notifica al padre via callbacks.
- **Modal local**: El modal de vista es local al componente, no requiere estado global.
- **Paginación manual**: Implementación propia con ellipsis, no usa librería externa.
- **Slots para actions**: Los botones de editar no están en `ExpedientesList` — están dentro de cada `ExpedienteCard`.
