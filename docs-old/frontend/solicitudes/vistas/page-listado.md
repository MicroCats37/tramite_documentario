# Page Listado — Gestión de Solicitudes

## Componente: `ShellSolicitudes`

**Ubicación**: `src/app/dashboard/solicitudes/_components/ShellSolicitudes.tsx`

Es el shell que envuelve todo el listado. Orchestrates tabs, filtros, buscador y el componente `SolicitudList`.

---

## Manejo de Estados

### Estado Local (useState)

```typescript
const [tempFilters, setTempFilters] = useState({
  estado: searchParams.get("estado") || undefined,
  finalizado: searchParams.get("finalizado") || undefined,
});
```

- **`tempFilters`**: Copia temporal de los filtros antes de aplicar. Permite que el usuario configure filtros y solo se apliquen al hacer click en "Aplicar".

### Estado desde URL (useSearchParams)

```typescript
const viewType = searchParams.get("view") || "";
const page = Number(searchParams.get("page")) || 1;
const search = searchParams.get("search") || "";
const ordering = searchParams.get("ordering") || "-fecha_creacion";
const estadoUrl = searchParams.get("estado") || undefined;
const finalizadoUrl = searchParams.get("finalizado") || undefined;
```

- **Fuente única de verdad**: Todos los filtros y el view activo se derivan de la URL. Esto hace el estado compartible via enlace directo.

### memoParams (useMemo)

```typescript
const hookParams = useMemo(
  () => ({
    limit: ITEMS_PER_PAGE,
    offset: (page - 1) * ITEMS_PER_PAGE,
    search: search || undefined,
    estado: estadoUrl,
    finalizado: finalizadoUrl,
    ordering,
  }),
  [page, search, estadoUrl, finalizadoUrl, ordering]
);
```

- **Memoizado**: Los params se memoizan para que la query key sea estable entre renders. Sin esto, cada render generaría una nueva referencia de objeto, causando refetches innecesarios.

---

## Actualización de URL

```typescript
const updateQueryParams = (newParams: Record<string, string | number | undefined>) => {
  const params = new URLSearchParams(searchParams.toString());
  Object.entries(newParams).forEach(([key, value]) => {
    if (value === undefined || value === "" || value === "all") {
      params.delete(key);
    } else {
      params.set(key, String(value));
    }
  });
  router.push(`${pathname}?${params.toString()}`);
};
```

- **URL como estado de la UI**: En lugar de almacenar filtros en estado local de React, se escriben en la URL. Esto permite que al refrescar la página se mantenga el estado de la vista.
- **Normalización**: Valores vacíos, `undefined` o `"all"` se eliminan de la URL para mantenerla limpia.

---

## Estructura de Vistas Declarativas

```typescript
const SOLICITUDES_VIEWS = [
  { value: undefined, label: "Todas", icon: List },
  { value: "asignadas", label: "Asignadas a mí", icon: UserCheck },
  { value: "adjuntadas", label: "Adjuntadas a mi", icon: Users },
  { value: "creadas", label: "Creadas por mí", icon: FilePlus },
  { value: "mi-area", label: "Mi Área", icon: Building2 },
] as const;
```

- **Declarativo**: Cada pestaña es un objeto con `value` (usado en la URL y como clave del ENDPOINT_MAP), `label` y `icon`. No hay lógica condicional para renderizar cada pestaña.

---

## Filtros Avanzados (Modal)

Los filtros de Estado y Finalizado usan un modal (`DataTableFilterModal`) con estado temporal que se aplica al confirmar:

```typescript
const handleApplyFilters = () => {
  updateQueryParams({ estado: tempFilters.estado, finalizado: tempFilters.finalizado, page: 1 });
};

const handleResetFilters = () => {
  updateQueryParams({ estado: undefined, finalizado: undefined, page: 1 });
  setTempFilters({ estado: undefined, finalizado: undefined });
};
```

---

## Fetching con Hook Dinámico

```typescript
const {
  data: dataResponse,
  isLoading,
  isError
} = useFetchSolicitudesDinamicas(viewType, hookParams);
```

- **Un solo hook**: Reemplaza los 5 hooks individuales que existirían con una estrategia por pestaña.
- **`dataResponse`**: Contiene `count`, `next`, `previous` y `results` (array de `SolicitudCard`).

---

## Paso de Datos a `SolicitudList`

```typescript
<SolicitudList
  user={user}
  data={activeResults}
  isLoading={isLoading}
  error={isError ? new Error("Error al cargar") : null}
  currentPage={page}
  totalPages={Math.ceil(totalCount / ITEMS_PER_PAGE)}
  totalItems={totalCount}
  pageSize={ITEMS_PER_PAGE}
  onPageChange={(p) => updateQueryParams({ page: p })}
/>
```

| Prop | Descripción |
|------|-------------|
| `data` | Array de `SolicitudCard` resultados de la query |
| `isLoading` | Estado de carga para mostrar skeleton/loading |
| `error` | Objeto Error si `isError` es true |
| `currentPage` | Página activa (derivada de URL) |
| `totalPages` | Cálculo basado en `count / ITEMS_PER_PAGE` |
| `onPageChange` | Callback que actualiza `page` en URL |
