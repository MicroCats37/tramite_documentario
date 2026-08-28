# Hook de Comentarios y Caché de React Query

## Archivos

- **Hook**: `src/app/dashboard/solicitudes/_hooks/useComentariosSolicitud.tsx`
- **Utils de caché**: `src/lib/react-query/cache-utils.ts`

## Hooks disponibles

| Hook | Acción | Método HTTP |
|------|--------|------------|
| `usePostComentario` | Crear comentario o respuesta | `POST /api/comentarios-solicitud/` |
| `useDeleteComentario` | Eliminar comentario | `DELETE /api/comentarios-solicitud/:id` |

## `usePostComentario`

```typescript
export const usePostComentario = ({ solicitudId, expedienteId }) => {
    const queryClient = useQueryClient();

    return useApiCreate<ComentarioType, FormData>({
        url: `/api/comentarios-solicitud/`,
        options: {
            onSuccess: (newComentario) => { ... },
            onError: (error: Error) => { ... },
        },
    });
};
```

### Operaciones de caché en `onSuccess`

#### 1. `appendNestedItemInCache` — Array anidado

```typescript
appendNestedItemInCache<SolicitudCard, ComentarioType>(
    queryClient,
    SOLICITUDES_QUERY_KEY,   // ['solicitudes']
    solicitudId,              // ID de la solicitud
    "comentarios",            // nombre del campo array en el objeto
    newComentario             // nuevo comentario a insertar
);
```

Busca en el caché de React Query una entrada que matchee `['solicitudes', {filters}, 'detail', solicitudId]` o la lista de solicitudes. Inserta `newComentario` en el campo `comentarios` del objeto `SolicitudCard` correspondiente.

**Propósito**: evitar un refetch completo — el nuevo comentario aparece instantáneamente en la UI.

#### 2. `appendCommentToExpedienteList` — Sincronización cruzada

```typescript
appendCommentToExpedienteList(
    queryClient,
    EXPEDIENTES_QUERY_KEY,    // ['expedientes']
    solicitudId,
    newComentario
);
```

Cuando un usuario comenta desde la página de solicitudes, el contador de comentarios en `ExpedienteCard` (que aparece en la lista de expedientes) también se actualiza. Sin esta función, el ExpedienteCard seguiría mostrando un contador desactualizado.

#### 3. `invalidateQueries` — Invalidación directa

```typescript
queryClient.invalidateQueries({
    queryKey: [...SOLICITUDES_QUERY_KEY, "detail", solicitudId],
});
```

Invalida específicamente el detalle de la solicitud para cubrir el caso en que el comentario se creó desde otra sesión o cuando la mutación optimista no es suficiente.

Si se pasó `expedienteId`, también invalida el detalle del expediente:

```typescript
if (expedienteId) {
    queryClient.invalidateQueries({
        queryKey: [...EXPEDIENTES_QUERY_KEY, "detail", expedienteId],
    });
}
```

## `useDeleteComentario`

```typescript
export const useDeleteComentario = ({ solicitudId, expedienteId }) => {
    const const queryClient = useQueryClient();
    return useApiDelete({
        baseUrl: "/api/comentarios-solicitud",
        options: {
            onSuccess: (_data, comentarioId) => {
                removeNestedItemFromCache<SolicitudCard, ComentarioType>(
                    queryClient,
                    SOLICITUDES_QUERY_KEY,
                    solicitudId,
                    "comentarios",
                    comentarioId
                );
                queryClient.invalidateQueries({
                    queryKey: [...SOLICITUDES_QUERY_KEY, "detail", solicitudId],
                });
            },
        },
    });
};
```

### Operaciones de caché en `onSuccess`

| Función | Qué hace |
|---------|-----------|
| `removeNestedItemFromCache` | Elimina el comentario con `comentarioId` del array `comentarios` dentro de la `SolicitudCard` en caché |
| `invalidateQueries` | Invalida el detalle de la solicitud (y del expediente si aplica) |

## Keys de consulta usados

| Key | Descripción |
|-----|-------------|
| `SOLICITUDES_QUERY_KEY` | `['solicitudes']` — lista y detalle de solicitudes |
| `EXPEDIENTES_QUERY_KEY` | `['expedientes']` — lista y detalle de expedientes |

## Uso en componentes

### En `CommentSection` → `CommentDialog`

```typescript
// CommentDialog.tsx
const postComentarioMutation = usePostComentario({ solicitudId, expedienteId });
```

`CommentDialog` recibe `solicitudId` y opcionalmente `expedienteId` y los pasa al hook.

### En `CommentItem` (para respuestas)

```typescript
// CommentItem.tsx — renderiza CommentDialog con parentComment
<CommentDialog
    isOpen={isReplyDialogOpen}
    onClose={() => setIsReplyDialogOpen(false)}
    solicitudId={solicitudId}
    expedienteId={expedienteId}
    parentComment={comment}  // pasa el comentario padre
/>
```

## Notas de diseño

- **Optimistic update via `appendNestedItemInCache`**: el comentario se inserta directamente en el caché existente sin esperar el refetch. Esto da una experiencia instantánea.
- **Sincronización cruzada Expediente**: `appendCommentToExpedienteList` es la función que mantiene coherentes las dos vistas (solicitudes y expedientes) cuando ambas muestran contadores de actividad.
- **Dual invalidation**: tanto `onSuccess` de la mutación como `invalidateQueries` trabajan juntos — el append optimisto cubre el caso inmediato, y la invalidación garantiza consistencia eventual incluso si hay race conditions.
