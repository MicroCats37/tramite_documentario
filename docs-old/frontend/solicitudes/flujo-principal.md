# Flujo Principal — Solicitudes (Lote 1: Núcleo y Vistas)

## ENDPOINT_MAP: Arquitectura de Vistas Dinámicas

El `ENDPOINT_MAP` es un diccionario declarativo que mapea cada pestaña de solicitud a su endpoint REST correspondiente:

```typescript
// src/app/dashboard/solicitudes/_hooks/useSolicitudes.ts
const ENDPOINT_MAP: Record<string, string> = {
  "": "/api/solicitudes/?view=card",           // Vista por defecto: Todas
  "asignadas": "/api/solicitudes/asignadas/?view=card",
  "creadas": "/api/solicitudes/creadas/?view=card",
  "mi-area": "/api/solicitudes/mi-area/?view=card",
  "adjuntadas": "/api/solicitudes/adjuntadas/?view=card",
};
```

### Diseño

- **Sin duplicación de hooks**: Un solo hook (`useFetchSolicitudesDinamicas`) reemplaza los 5 hooks individuales que existirían si cada pestaña tuviera su propio hook.
- **Extensibilidad**: Agregar una nueva pestaña solo requiere agregar una entrada al `ENDPOINT_MAP` y una opción en `SOLICITUDES_VIEWS` en `ShellSolicitudes.tsx`.

---

## Prefetch Inteligente (onMouseEnter)

```typescript
// ShellSolicitudes.tsx — handlePrefetch
const handlePrefetch = (targetView: string | undefined) => {
  const prefetchParams = { ...hookParams, offset: 0 }; // Siempre página 1

  queryClient.prefetchQuery({
    queryKey: [...SOLICITUDES_QUERY_KEY, nextView, prefetchParams],
    queryFn: () => fetchSolicitudesFn(nextView, prefetchParams),
    staleTime: 1000 * 60 * 5, // 5 minutos
  });
};
```

### Mecanismo

1. **Disparador**: `onMouseEnter` en cada botón de pestaña.
2. **Timing**: La query se inicia en el hover, antes del click. Cuando el usuario hace click, los datos ya están en caché.
3. **Key coincidente**: La `queryKey` usa la misma estructura que el hook, garantizando que React Query sirv a la misma entrada cacheada.
4. **Offset forzado a 0**: Siempre hace prefetch de la página 1 porque los botones de pestaña resetean la página al cambiar de vista.

---

## Hooks Principales

### `useFetchSolicitudesDinamicas(viewType, params)`

Hook dinámico que consume cualquier endpoint del `ENDPOINT_MAP` según el `viewType` activo.

**Puntos clave**:
- `queryKey: [...SOLICITUDES_QUERY_KEY, currentView, params]` — La clave incluye la vista actual para separar cachés.
- `staleTime: 1000 * 60 * 5` — Los datos se consideran frescos por 5 minutos.
- `placeholderData: (previousData) => previousData` — Mantiene los datos anteriores visibles durante la carga (elimina parpadeos).

### `useFetchSolicitudById(id)`

Para la vista de detalle de una sola solicitud.

- `enabled: !!id` — No ejecuta la query si no hay ID.
- Retry: 2 intentos, excepto para 404 (error fatal inmediato).

### Mutations (Create / Update / Delete)

| Hook | Caché Strategy | Efecto colateral |
|------|---------------|-----------------|
| `useCreateSolicitud` | `prependToPaginatedCache` | Agrega la nueva solicitud al inicio de todas las listas |
| `useUpdateSolicitud` | `mergeUpdateInPaginatedCache` | Actualiza la solicitud preservando el `expediente` del caché viejo |
| `useDeleteSolicitud` | `removeFromPaginatedCache` | Elimina la solicitud de todas las listas paginadas |

Todas las mutations invalidan `EXPEDIENTES_QUERY_KEY` para sincronizar la otra vista.

---

## Caché Utils (react-query)

### `prependToPaginatedCache`
Agrega un item al inicio de todas las listas paginadas que coincidan con la query key.

### `mergeUpdateInPaginatedCache`
Hace un merge profundo de la solicitud actualizada, pero preserva campos específicos (como `expediente`) del caché anterior para evitar perder datos.

### `removeFromPaginatedCache`
Elimina un item por ID de todas las listas cacheadas.

---

## Flujo de Datos (Lectura)

```
URL: ?view=asignadas&page=2&search=EXP-001&estado=PENDIENTE
        ↓
ShellSolicitudes.tsx extrae viewType y hookParams (memoizados)
        ↓
useFetchSolicitudesDinamicas(viewType, hookParams)
        ↓
queryKey: ["solicitudes", "asignadas", { limit: 10, offset: 10, search: "EXP-001", ... }]
        ↓
useApiQuery → api.get(ENDPOINT_MAP["asignadas"], { params: hookParams })
        ↓
Respuesta → SolicitudPaginatedResponseSchema (Zod)
        ↓
React Query actualiza caché + componente re-renderiza con dataResponse.results
```

---

## Archivos del Núcleo

| Archivo | Rol |
|---------|-----|
| `src/app/dashboard/solicitudes/_hooks/useSolicitudes.tsx` | ENDPOINT_MAP, hooks de fetch y mutations |
| `src/app/dashboard/solicitudes/_hooks/useSolicitudUI.tsx` | Configuración de secciones de formulario según permisos |
| `src/app/dashboard/solicitudes/_components/ShellSolicitudes.tsx` | Shell con tabs, filtros, buscador y prefetch |
| `src/app/dashboard/solicitudes/_components/SolicitudList.tsx` | Componente de listado que consume data del hook |
