# ShellExpedientes

**Responsabilidad**: Contenedor principal del módulo Expedientes. Gestiona el estado global de modales, la orquestación del flujo encadenado Crear Expediente → Crear Solicitud, y la paginación via URL params.

**Ubicación**: `frontend/src/app/dashboard/expedientes/_components/ShellExpedientes.tsx`

---

## Arquitectura de Estado

### Estado Local (React useState)

| Estado | Tipo | Propósito |
|--------|------|-----------|
| `user` | `LoginUserData \| undefined` | Usuario autenticado cargado desde cookie |
| `isModalExpedienteOpen` | `boolean` | Controla visibilidad del modal de crear/editar expediente |
| `isModalSolicitudOpen` | `boolean` | Controla visibilidad del modal de crear/editar solicitud |
| `selectedExpediente` | `Expediente \| null` | Expediente seleccionado para edición; `null` = modo creación |

### Estado Derivado de URL (useSearchParams)

| Param | Tipo | Default | Propósito |
|-------|------|---------|-----------|
| `view` | `ViewType` (`"todos"` \| `"mis-expedientes"` \| `"sin-solicitud"`) | `"todos"` | Filtro de vista |
| `page` | `number` | `1` | Página actual |
| `search` | `string` | `""` | Término de búsqueda |
| `ordering` | `string` | `"-fecha_creacion"` | Ordenamiento |

---

## Props del Componente

**No recibe props** — es un componente de página (`"use client"`) que obtiene todo de su contexto (auth, router, searchParams).

---

## Flujo Encadenado de Modales (Chain Flow)

### Creación de Expediente → Solicitud

```
User clic "Nuevo Expediente"
  → handleOpenCreate()
    → setSelectedExpediente(null)
    → setIsModalExpedienteOpen(true)
      → ModalExpedienteForm abierto (modo crear)

User llena formulario y guarda
  → handleSaveExpediente(data)
    ├── Si EDICIÓN: mutateAsync(update) → setIsModalExpedienteOpen(false) [fin]
    └── Si CREACIÓN:
        1. mutateAsync(create) → nuevoExpediente
        2. setIsModalExpedienteOpen(false)
        3. setSelectedExpediente(nuevoExpediente)
        4. setTimeout(150ms) → setIsModalSolicitudOpen(true)
          → ModalSolicitudForm abierto (modo crear, pre-rellenado con expediente)
```

### Puntos Clave del Chain

1. **150ms delay**: Permite que el modal de expediente se cierre visualmente antes de abrir el de solicitud (suavidad).
2. **selectedExpediente persiste**: No se limpia entre el cierre del modal expediente y la apertura del modal solicitud — mantiene el contexto.
3. **Re-lanzado de errores**: Si `onSave` falla, el error se re-lanza (`throw error`) para que el modal hijo sepa que la operación falló y NO cierre.

---

## Fetching de Datos

### Hook: `useFetchExpedientesDinamicos(viewType, hookParams)`

```typescript
const hookParams = useMemo(() => ({
  limit: ITEMS_PER_PAGE,      // 10
  offset: (page - 1) * 10,    // 0, 10, 20, ...
  search: search || undefined,
  ordering,
}), [page, search, ordering]);
```

### Smart Prefetch

```typescript
const handlePrefetch = (targetView: string) => {
  queryClient.prefetchQuery({
    queryKey: [...EXPEDIENTES_QUERY_KEY, targetView, { ...hookParams, offset: 0 }],
    queryFn: () => fetchExpedientesFn(targetView, prefetchParams),
    staleTime: 1000 * 60 * 5, // 5 minutos
  });
};
```

Se dispara en `onMouseEnter` de cada tab de vista — precarga datos al hacer hover.

---

## Componentes Hijos Renderizados

| Componente | Props | Propósito |
|------------|-------|----------|
| `SearchInput` | `initialValue={search}`, `onSearch` | Búsqueda con debounce |
| `ExpedientesList` | `user`, `expedientes`, `isLoading`, `onEditExpediente`, `onEditSolicitud`, `currentPage`, `totalPages`, `onPageChange` | Listado con cards y paginación |
| `ModalSolicitudForm` | `currentUser`, `isOpen`, `onClose`, `solicitud`, `expediente`, `onSave`, `isLoading` | Modal de solicitud |
| `ModalExpedienteForm` | `isOpen`, `onClose`, `expediente`, `onSave`, `isLoading` | Modal de expediente |

---

## Handlers

| Handler | Función |
|---------|---------|
| `handleOpenCreate` | Limpia `selectedExpediente`, abre modal expediente |
| `handleOpenEditExpediente(e)` | Fija `selectedExpediente = e`, abre modal expediente |
| `handleOpenEditSolicitud(e)` | Fija `selectedExpediente = e`, abre modal solicitud |
| `handleSaveExpediente(data)` | Orchestrates create/update + chain flow |
| `handleSaveSolicitud(data)` | Crea o actualiza solicitud según corresponda |
| `updateQueryParams(newParams)` | Actualiza URL con nuevos params, maneja valores vacíos |

---

## Constantes

```typescript
const ITEMS_PER_PAGE = 10;

const EXPEDIENTE_VIEWS = [
  { value: "todos", label: "Todos", icon: Files },
  { value: "mis-expedientes", label: "Mis Expedientes", icon: UserCircle },
  { value: "sin-solicitud", label: "Sin Solicitud", icon: FileWarning },
] as const;

type ViewType = "todos" | "mis-expedientes" | "sin-solicitud";
```

---

## Dependencias de Mutations

```typescript
const ExpedientecreateMutation = useCreateExpediente();
const ExpedienteupdateMutation = useUpdateExpediente();
const SolicitudcreateMutation = useCreateSolicitud();
const SolicitudupdateMutation = useUpdateSolicitud();
```

---

## Notas de Implementación

- **URL como fuente de verdad**: El estado de paginación, búsqueda y vista vive en la URL — navegable y bookmarkable.
- **QueryClient para prefetch**: Usa `@tanstack/react-query` para prefetchear vistas alternativas al hover.
- **Sin Zustand/Context**: Todo el estado es local al Shell; los hijos reciben callbacks del padre.
