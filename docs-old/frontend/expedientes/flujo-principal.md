# Flujo Principal — Expedientes (Frontend)

## Visión General

Módulo de gestión de expedientes digitales del sistema CIP. Utiliza **React Query (TanStack Query)** para gestión de estado servidor y caché, con invalidación manual para actualizaciones de latencia cero.

---

## Endpoints Consumidos

### Mapa de Endpoints por Vista

| Vista | Endpoint | Método | Descripción |
|-------|----------|--------|-------------|
| `todos` | `/api/expedientes/` | GET | Lista global de expedientes |
| `mis-expedientes` | `/api/expedientes/creadas/` | GET | Expedientes creados por el usuario autenticado |
| `sin-solicitud` | `/api/expedientes/creadas-sin-solicitud/` | GET | Expedientes sin flujo de trabajo asociado |
| detalle | `/api/expedientes/{id}/` | GET | Obtiene un expediente individual |

### Parámetros de Query

```typescript
type ExpedienteQueryParams = Record<string, string | number | boolean | undefined>;

// Parámetros estándar usados:
{
  limit: number;      // Items por página (default: 10)
  offset: number;     // Offset de paginación (page - 1) * 10
  search?: string;     // Búsqueda por DNI, RUC, CIP, nombres/apellidos
  ordering?: string;   // Campo de ordenamiento (default: "-fecha_creacion")
}
```

### Esquema de Respuesta Paginada

```typescript
const ExpedientePaginatedResponseSchema = z.object({
  count: z.number(),           // Total de registros
  next: z.string().nullable(), // URL siguiente página
  previous: z.string().nullable(), // URL página anterior
  results: z.array(ExpedienteSchema), // Array de expedientes
});
```

---

## Estados de React Query

### Query States para `useFetchExpedientesDinamicos`

```typescript
// Hook: useFetchExpedientesDinamicos(viewType, params)
const { data, isLoading, error, isFetching } = useFetchExpedientesDinamicos(viewType, params);

// Estados:
data?.results        // Expediente[] - datos de la página actual
data?.count         // number - total de registros
isLoading           // boolean - primera carga (sin datos en caché)
isFetching          // boolean - cualquier carga (incluye refetching)
error               // Error | null
```

### Query States para `useFetchExpedienteById`

```typescript
const { data: expediente, isLoading, error } = useFetchExpedienteById(id);

// Configuración:
{
  staleTime: 1000 * 60 * 30,  // 30 minutos
  enabled: !!id                // Solo ejecuta si hay ID válido
}
```

---

## Manejo de Caché

### Estrategias Implementadas

#### 1. staleTime Configurado
| Hook | staleTime | Razón |
|------|-----------|-------|
| `useFetchExpedientesDinamicos` | 5 minutos | Lista se actualiza frecuentemente |
| `useFetchExpedienteById` | 30 minutos | Detalle es más estable |

#### 2. placeholderData (Evitar Parpadeos)
```typescript
queryOptions: {
  staleTime: 1000 * 60 * 5,
  placeholderData: (previousData) => previousData, // Mantiene datos anteriores durante refetch
}
```

#### 3. Smart Prefetch on Tab Hover
```typescript
// ShellExpedientes.tsx - handlePrefetch
const handlePrefetch = (targetView: string) => {
  queryClient.prefetchQuery({
    queryKey: [...EXPEDIENTES_QUERY_KEY, targetView, prefetchParams],
    queryFn: () => fetchExpedientesFn(targetView, prefetchParams),
    staleTime: 1000 * 60 * 5,
  });
};
```

### Cache Keys

```typescript
// Base key para invalidación
const EXPEDIENTES_QUERY_KEY = ["expedientes"] as const;

// Keys específicas:
// ["expedientes", "todos", params]
// ["expedientes", "mis-expedientes", params]
// ["expedientes", "detail", id]
```

### Invalidación Manual

```typescript
// Función para invalidar TODAS las queries de expedientes
const invalidateExpedientesList = (queryClient: QueryClient) => {
  queryClient.invalidateQueries({ queryKey: EXPEDIENTES_QUERY_KEY });
};
```

---

## Mutaciones Principales

### 1. Crear Expediente — `useCreateExpediente`

```typescript
const useCreateExpediente = () => {
  return useApiCreate<Expediente, ExpedienteCreateFormData | FormData>({
    url: "/api/expedientes/",
    schema: ExpedienteSchema,
    options: {
      onSuccess: (nuevoExpediente) => {
        toast.success("Expediente creado correctamente");
        // Actualización manual de caché - LATENCIA CERO
        prependToPaginatedCache(queryClient, EXPEDIENTES_QUERY_KEY, nuevoExpediente);
      },
      onError: (error: Error) => toast.error(error.message),
    },
  });
};
```

**Estrategia de caché**: `prependToPaginatedCache` — agrega el nuevo expediente al inicio de todas las listas paginadas activas sin necesidad de refetch.

### 2. Actualizar Expediente — `useUpdateExpediente`

```typescript
const useUpdateExpediente = () => {
  return useApiUpdate<Expediente, FormData | ExpedienteUpdateFormData>({
    baseUrl: "/api/expedientes",
    method: "PATCH",
    options: {
      onSuccess: (expedienteActualizado) => {
        toast.success("Expediente actualizado correctamente");
        updateInPaginatedCache(queryClient, EXPEDIENTES_QUERY_KEY, expedienteActualizado);
      },
      onError: (error: Error) => toast.error(error.message),
    },
  });
};
```

**Estrategia de caché**: `updateInPaginatedCache` — actualiza el expediente modificado dentro de las listas activas.

### 3. Eliminar Expediente — `useDeleteExpediente`

```typescript
const useDeleteExpediente = () => {
  return useApiDelete({
    baseUrl: "/api/expedientes",
    options: {
      onSuccess: (_, id) => {
        toast.success("Expediente eliminado");
        removeFromPaginatedCache(queryClient, EXPEDIENTES_QUERY_KEY, id);
      },
      onError: (error: Error) => toast.error(error.message),
    },
  });
};
```

**Estrategia de caché**: `removeFromPaginatedCache` — remove el expediente de las listas activas.

### 4. Helper de Invalidación

```typescript
const invalidateExpedientesList = (queryClient: QueryClient) => {
  queryClient.invalidateQueries({ queryKey: EXPEDIENTES_QUERY_KEY });
};
```

---

## Utilidades de Caché (cache-utils)

### Funciones Disponibles

| Función | Propósito |
|---------|-----------|
| `prependToPaginatedCache` | Agrega item al inicio de lista paginada |
| `updateInPaginatedCache` | Actualiza item existente en lista paginada |
| `removeFromPaginatedCache` | Elimina item de lista paginada |

### Importación
```typescript
import {
  prependToPaginatedCache,
  updateInPaginatedCache,
  removeFromPaginatedCache
} from "@/lib/react-query/cache-utils";
```

---

## Integración con Módulo de Solicitudes

El expediente puede tener una `solicitud` asociada. Los componentes de detalle (`[id]/page.tsx`) integran:

- `useCreateSolicitud` — Crear flujo de trabajo para expediente
- `useUpdateSolicitud` — Actualizar estado del flujo

```typescript
// En page-detalle.tsx
const SolicitudcreateMutation = useCreateSolicitud();
const SolicitudupdateMutation = useUpdateSolicitud();

// Lógica de guardado unificada
const handleSaveSolicitud = async (data) => {
  if (expediente && !expediente.solicitud) {
    await SolicitudcreateMutation.mutateAsync(data);
  } else if (expediente?.solicitud) {
    await SolicitudupdateMutation.mutateAsync({ id: expediente.solicitud.id, data });
  }
};
```
