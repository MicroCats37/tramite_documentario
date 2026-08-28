# ShellSolicitudes

Orquesta toda la vista de gestión de solicitudes. Actúa como **layout principal** y **controlador de filtros/paginación**, delegando el renderizado a `SolicitudList`.

## Rol en la Arquitectura

- **Conainer component**: consume hooks de React Query, maneja URL search params, y pasa datos pre-procesados a `SolicitudList`.
- **No renderiza solicitudes directamente**: delega esa responsabilidad a `SolicitudList` y `SolicitudCard`.

## Estado Local

| Estado | Tipo | Propósito |
|--------|------|-----------|
| `user` | `LoginUserData \| undefined` | Usuario autenticado, obtenido del cookie al montar |
| `tempFilters` | `{ estado, finalizado }` | Filtros pendientes de aplicar (confirmación en dos pasos) |

## URL como Fuente de Verdad

Todos los parámetros de vista se gestionan via `searchParams`:

```
/dashboard/solicitudes?view=asignadas&page=2&estado=EN_GESTION_MP&finalizado=false&search=EXP-2024
```

| Parámetro | Fuente | Default |
|-----------|--------|---------|
| `view` | `searchParams.get("view")` | `""` (Todas) |
| `page` | `searchParams.get("page")` | `1` |
| `search` | `searchParams.get("search")` | `""` |
| `ordering` | `searchParams.get("ordering")` | `-fecha_creacion` |
| `estado` | `searchParams.get("estado")` | `undefined` |
| `finalizado` | `searchParams.get("finalizado")` | `undefined` |

## Flujo de Datos

```
useFetchSolicitudesDinamicas(viewType, hookParams)
  └─> dataResponse.results  -->  activeResults  -->  SolicitudList
  └─> dataResponse.count   -->  totalCount     -->  SolicitudList + Tabs badge
```

## Vistas Declarativas

Definidas en `SOLICITUDES_VIEWS` (constante en el módulo):

| value | label | Descripción |
|-------|-------|-------------|
| `undefined` | Todas | Todas las solicitudes |
| `"asignadas"` | Asignadas a mí | WHERE usuario_asignado = current_user |
| `"adjuntadas"` | Adjuntadas a mi | WHERE current_user IN usuarios_adjuntados |
| `"creadas"` | Creadas por mí | WHERE created_by = current_user |
| `"mi-area"` | Mi Área | WHERE area_responsable = current_user.area |

## Prefetch Inteligente (TanStack Query)

```typescript
onMouseEnter={() => handlePrefetch(value)}
```

Al hacer hover sobre un tab, precarga la primera página de esa vista con `staleTime: 5min`. Esto hace que el cambio de vista sea instantáneo.

## Patrón de Actualización de Params

```typescript
const updateQueryParams = (newParams) => {
  const params = new URLSearchParams(searchParams.toString());
  // Si value === undefined | "" | "all" → se elimina el parámetro
  // Si tiene valor → se establece
  router.push(`${pathname}?${params.toString()}`);
};
```

## Dependencias

- `@tanstack/react-query`: `queryClient.prefetchQuery`
- `next/navigation`: `useRouter`, `usePathname`, `useSearchParams`
- `../_hooks/useSolicitudes`: `useFetchSolicitudesDinamicas`, `fetchSolicitudesFn`, `SOLICITUDES_QUERY_KEY`
