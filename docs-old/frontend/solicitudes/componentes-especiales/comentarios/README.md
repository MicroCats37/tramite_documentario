# Subsistema de Comentarios — Solicitudes

## Resumen

El subsistema de comentarios implementa un hilo de conversación anidado (árbol recursivo) para las solicitudes del módulo de mesa de partes. Permite crear comentarios, responder a otros (hasta una profundidad máxima de 3 niveles), adjuntar archivos, y mantener el caché de React Query sincronizado sin recargas.

## Estructura de archivos

```
src/app/dashboard/solicitudes/_components/comentarios/
├── index.ts                     # Barril de exports
├── ComentariosSolicitud.tsx     # (vacío — archivo reservado)
├── CommentSection.tsx           # Contenedor principal + layout
├── CommentItem.tsx              # Componente recursivo de comentario
├── CommentDialog.tsx            # Modal de creación / respuesta
└── utils/
    ├── index.ts
    ├── buildCommentTree.ts      # Conversión lista plana → árbol
    └── formatters.ts            # Formatadores de fecha
```

## Hooks relacionados

```
src/app/dashboard/solicitudes/_hooks/
└── useComentariosSolicitud.tsx   # usePostComentario, useDeleteComentario
```

## Componentes

| Componente | Rol |
|-----------|-----|
| `CommentSection` | Layout contenedor (header + scroll + footer). Construye el árbol con `buildCommentTree`. |
| `CommentItem` | Componente **recursivo** que se llama a sí mismo para `children`. Renderiza un comentario + sus respuestas anidadas. |
| `CommentDialog` | Modal con `GenericForm` para crear comentario nuevo o responder a uno existente. |
| `buildCommentTree` | Utility que convierte la lista plana de comentarios de la API en un árbol jerárquico. |

## Artículos de esta sección

1. **[Árbol recursivo de comentarios](./arbol-recursivo.md)** — Cómo funciona `buildCommentTree` y el renderizado recursivo en `CommentItem`.
2. **[Profundidad máxima (maxDepth)](./profundidad-maxima.md)** — El límite de anidación (default 3), cómo se aplica y qué pasa cuando se excede.
3. **[Flujo de creación de comentario y respuesta](./flujo-creacion.md)** — Recorrido end-to-end desde que el usuario abre el diálogo hasta que el comentario aparece en pantalla.
4. **[Hook de comentarios y caché de React Query](./hook-cache.md)** — `usePostComentitud` y `useDeleteComentario`: qué funciones de caché invocan y por qué se invalidan consultas relacionadas.
