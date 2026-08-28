# Flujo de Creación de Comentario y Respuesta

## Diagrama de flujo

```
Usuario hace clic
       │
       ▼
┌─────────────────────────────┐
│  CommentSection → Footer    │
│  Botón "Escribir comentario"│
└──────────────┬──────────────┘
               │ onClick → setIsDialogOpen(true)
               ▼
┌─────────────────────────────┐
│  CommentDialog (Modal)       │
│  GenericForm + AnexosManager│
└──────────────┬──────────────┘
               │ onSubmit → handleSubmit
               ▼
┌─────────────────────────────┐
│  usePostComentario.mutateAsync│
│  POST /api/comentarios-solicitud/
└──────────────┬──────────────┘
               │
       ┌───────┴───────┐
       │   onSuccess   │
       ▼               ▼
┌──────────────┐  ┌──────────────┐
│appendNested  │  │appendComment │
│ItemInCache   │  │ToExpediente  │
│(SOLICITUDES) │  │List          │
└──────┬───────┘  └──────────────┘
       │
       ▼
┌──────────────────────────────┐
│  invalidateQueries            │
│  [...SOLICITUDES_QUERY_KEY,  │
│   "detail", solicitudId]      │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  React Query re-fetch         │
│  → CommentSection re-render  │
│  → Árbol reconstruido        │
└──────────────────────────────┘
```

## Paso a paso

### 1. Apertura del diálogo

**Trigger**: clic en el botón del footer de `CommentSection`.

- `CommentSection` mantiene `isDialogOpen` en estado local.
- Se renderiza `<CommentDialog isOpen={isDialogOpen} ... />`.

Para **respuesta a un comentario** específico:
- El botón de reply en `CommentItem` abre `isReplyDialogOpen` (estado local de `CommentItem`).
- Se pasa `parentComment={comment}` al `CommentDialog`.

### 2. Formulario en `CommentDialog`

`CommentDialog` usa `GenericForm<ComentarioCreateForm>` con el schema `ComentarioFormCreateSchema` y la configuración UI de `comentarioUI`.

Campos:
- `texto` — contenido del comentario (requerido).
- `anexos` — lista de archivos adjuntos (opcional).
- `parent` — se inyecta como `parentComment?.id` en los initial data cuando es respuesta.

### 3. Submit handler

```typescript
const handleSubmit: SubmitHandler<ComentarioCreateForm> = async (values) => {
    const payloadData = {
        ...values,
        solicitud: solicitudId,       // siempre se incluye
    };

    if (values.anexos?.length > 0) {
        payloadData.anexos = prepareAnexosPayload(values.anexos);
    } else {
        payloadData.anexos = [];
    }

    const finalPayload = buildApiPayload(payloadData); // FormData o JSON
    await postComentarioMutation.mutateAsync(finalPayload as FormData);
    onClose();
};
```

### 4. Llamado API

`usePostComentario` usa `useApiCreate` internamente:

```typescript
url: `/api/comentarios-solicitud/`
method: POST
```

El payload incluye:
- `texto`: string
- `solicitud`: ID de la solicitud
- `parent`: ID del comentario padre (solo si es respuesta)
- `anexos`: array de anexos procesados

### 5. Respuesta de la API

La API devuelve el objeto `ComentarioType` completo del nuevo comentario creado, con su `id` generado por el backend.

### 6. Actualización del caché (onSuccess)

`usePostComentario.onSuccess` hace tres cosas:

```typescript
// a) Agrega el comentario al array anidado de la solicitud en caché
appendNestedItemInCache<SolicitudCard, ComentarioType>(
    queryClient,
    SOLICITUDES_QUERY_KEY,
    solicitudId,
    "comentarios",
    newComentario
);

// b) También actualiza la lista de Expedientes (contador de comentarios)
appendCommentToExpedienteList(queryClient, EXPEDIENTES_QUERY_KEY, solicitudId, newComentario);

// c) Invalida el detalle de la solicitud para garantizar consistencia
queryClient.invalidateQueries({
    queryKey: [...SOLICITUDES_QUERY_KEY, "detail", solicitudId],
});
```

### 7. Re-render

React Query detecta el cambio en el caché de `comentarios` dentro de la `SolicitudCard`. `CommentSection` recibe nuevos props → `buildCommentTree` se re-ejecuta → el nuevo comentario aparece en pantalla sin recargar la página.

## Flujo para respuesta (diferencias)

| Paso | Comentario nuevo | Respuesta |
|------|-----------------|-----------|
| `parentComment` | `undefined` | pasa el comentario padre |
| `parent` en payload | no se incluye | `parentComment.id` |
| Título del diálogo | "Nuevo Comentario" | "Responder a {nombre}" |
| Icono | `MessageSquare` | `Reply` |
| Cita del padre | no | muestra `parentComment.texto` en cursiva |
|Texto del botón | "Publicar Comentario" | "Enviar Respuesta" |

## Auto-scroll

`CommentSection` tiene un `useEffect` que hace scroll suave al fondo cuando `totalComentarios` cambia:

```typescript
useEffect(() => {
    if (scrollContainerRef.current && totalComentarios > 0) {
        scrollContainerRef.current.scrollTo({
            top: scrollContainerRef.current.scrollHeight,
            behavior: "smooth",
        });
    }
}, [totalComentarios]);
```
