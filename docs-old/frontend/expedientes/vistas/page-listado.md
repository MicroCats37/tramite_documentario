# Vista: Page Listado — Expedientes

## Archivo Principal

**Ruta**: `frontend/src/app/dashboard/expedientes/page.tsx`

**Componente contenedor**: `ShellExpedientes` (`_components/ShellExpedientes.tsx`)

---

## Propagación de Props

### Flujo de Datos Principal

```
page.tsx
  └── ShellExpedientes (contenedor principal)
        ├── SearchInput (búsqueda)
        ├── Tabs de vistas (3 opciones)
        ├── ExpedientesList (listado)
        │     ├── ExpedienteCard × N (cada item)
        │     └── Paginación
        ├── ModalExpedienteForm (crear/editar)
        └── ModalSolicitudForm (gestionar flujo)
```

### Props del ShellExpedientes (Estado Interno)

```typescript
// Estado local del componente
const [user, setUser] = useState<LoginUserData | undefined>(undefined);
const [isModalExpedienteOpen, setIsModalExpedienteOpen] = useState(false);
const [isModalSolicitudOpen, setIsModalSolicitudOpen] = useState(false);
const [selectedExpediente, setSelectedExpediente] = useState<Expediente | null>(null);

// Estado derivado de URL
const viewType = searchParams.get("view") as ViewType;  // 'todos' | 'mis-expedientes' | 'sin-solicitud'
const page = Number(searchParams.get("page")) || 1;
const search = searchParams.get("search") || "";
const ordering = searchParams.get("ordering") || "-fecha_creacion";
```

### Props de ExpedientesList

```typescript
interface ExpedientesListProps {
  user: LoginUserData;              // Usuario autenticado
  expedientes: Expediente[];        // Resultados de la página actual
  isLoading: boolean;               // Estado de carga
  onEditExpediente: (exp: Expediente) => void;  // Abrir modal editar expediente
  onEditSolicitud: (exp: Expediente) => void;   // Abrir modal gestionar solicitud
  currentPage: number;              // Página actual
  totalPages: number;              // Total de páginas
  onPageChange: (page: number) => void;  // Callback cambio de página
}
```

---

## Estado de Búsqueda y Paginación

### searchParams de URL

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `view` | `ViewType` | `"todos"` | Vista activa: `todos`, `mis-expedientes`, `sin-solicitud` |
| `page` | `number` | `1` | Página actual (1-indexed) |
| `search` | `string` | `""` | Término de búsqueda |
| `ordering` | `string` | `"-fecha_creacion"` | Campo de ordenamiento (prefix `-` = descendente) |

### Conversión Offset/Limit para API

```typescript
const ITEMS_PER_PAGE = 10;

const hookParams = useMemo(() => ({
  limit: ITEMS_PER_PAGE,
  offset: (page - 1) * ITEMS_PER_PAGE,  // Convierte página 1-indexed a offset 0-indexed
  search: search || undefined,
  ordering,
}), [page, search, ordering]);
```

### Actualización de URL

```typescript
const updateQueryParams = (newParams: Record<string, string | number | undefined>) => {
  const params = new URLSearchParams(searchParams.toString());
  Object.entries(newParams).forEach(([key, value]) => {
    if (value === undefined || value === "" || value === "all")
      params.delete(key);
    else params.set(key, String(value));
  });
  router.push(`${pathname}?${params.toString()}`);
};
```

---

## Subcomponentes

### 1. Tabs de Vista (`EXPEDIENTE_VIEWS`)

```typescript
const EXPEDIENTE_VIEWS = [
  { value: "todos", label: "Todos", icon: Files },
  { value: "mis-expedientes", label: "Mis Expedientes", icon: UserCircle },
  { value: "sin-solicitud", label: "Sin Solicitud", icon: FileWarning },
] as const;
```

**Comportamiento**:
- Al hacer hover sobre una tab → `handlePrefetch(value)` precarga datos de esa vista
- Al hacer click → `updateQueryParams({ view: value, page: 1 })` cambia vista y resetea página
- Muestra count total cuando la vista está activa: `(${totalCount})`

### 2. SearchInput

```typescript
<SearchInput
  placeholder="Buscar por DNI, RUC, CIP, Nombres y Apellidos"
  initialValue={search}
  onSearch={(val) => updateQueryParams({ search: val, page: 1 })}
/>
```

**Comportamiento**:
- Cambio en búsqueda → actualiza URL con `search=val` y `page=1`
- Debounced automáticamente por el componente

### 3. ExpedientesList

Renderiza lista de `ExpedienteCard` y controles de paginación.

### 4. ModalExpedienteForm

```typescript
<ModalExpedienteForm
  isOpen={isModalExpedienteOpen}
  onClose={() => setIsModalExpedienteOpen(false)}
  expediente={selectedExpediente}  // null = crear, Expediente = editar
  onSave={handleSaveExpediente}
  isLoading={ExpedientecreateMutation.isPending || ExpedienteupdateMutation.isPending}
/>
```

### 5. ModalSolicitudForm

```typescript
<ModalSolicitudForm
  currentUser={user!}
  isOpen={isModalSolicitudOpen}
  onClose={() => setIsModalSolicitudOpen(false)}
  solicitud={selectedExpediente?.solicitud}
  expediente={selectedExpediente}
  onSave={handleSaveSolicitud}
  isLoading={SolicitudcreateMutation.isPending || SolicitudupdateMutation.isPending}
/>
```

---

## Flujo de Creación encadenado

```typescript
const handleSaveExpediente = async (data) => {
  if (selectedExpediente) {
    // Modo edición
    await ExpedienteupdateMutation.mutateAsync({
      id: selectedExpediente.id,
      data: data as ExpedienteUpdateFormData,
    });
    setIsModalExpedienteOpen(false);
  } else {
    // Modo creación → abrir modal de solicitud inmediatamente
    const nuevoExpediente = await ExpedientecreateMutation.mutateAsync(data);
    setIsModalExpedienteOpen(false);
    setSelectedExpediente(nuevoExpediente);
    setTimeout(() => setIsModalSolicitudOpen(true), 150);
  }
};
```

**Flujo**:
1. Usuario crea expediente → se guarda en DB
2. Modal crear expediente se cierra
3. `setSelectedExpediente(nuevoExpediente)` guarda referencia
4. `setTimeout(..., 150)` retrasa apertura 150ms para suavidad visual
5. Se abre `ModalSolicitudForm` para iniciar flujo de trabajo

---

## Smart Prefetch

```typescript
const handlePrefetch = (targetView: string) => {
  const prefetchParams = {
    ...hookParams,
    offset: 0,  // Siempre página 1 al prefetchar
  };

  queryClient.prefetchQuery({
    queryKey: [...EXPEDIENTES_QUERY_KEY, targetView, prefetchParams],
    queryFn: () => fetchExpedientesFn(targetView, prefetchParams),
    staleTime: 1000 * 60 * 5,
  });
};
```

**Trigger**: `onMouseEnter` de cada tab de vista
