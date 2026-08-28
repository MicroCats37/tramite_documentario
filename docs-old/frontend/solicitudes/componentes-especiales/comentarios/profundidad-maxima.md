# Profundidad Máxima (maxDepth)

## Valor por defecto

`maxDepth = 3` (definido en `CommentItem` como valor por defecto del parámetro `depth`).

Esto significa que un comentario de nivel 0 (raíz) puede tener hijos de nivel 1, 2 y 3. En nivel 3, ya no se permite abrir respuestas directamente.

## Cómo funciona la lógica de profundidad

En `CommentItem`, la prop `depth` indica el nivel actual en el árbol:

```
depth = 0  → Comentario raíz (primer nivel)
depth = 1  → Respuesta a raíz
depth = 2  → Respuesta a respuesta
depth = 3  → Cuarto nivel (MÁXIMO) — no se pueden responder estos
```

### Regla de renderizado

```typescript
{depth >= maxDepth ? (
    // ▼ EXCEDE: hijos colapsados en Collapsible
    <Collapsible>
        <CollapsibleTrigger>Ver N respuestas</CollapsibleTrigger>
        <CollapsibleContent>
            {comment.children.map(child => (
                <CommentItem ... depth={depth + 1} />
            ))}
        </CollapsibleContent>
    </Collapsible>
) : (
    // ▼ DENTRO DEL LÍMITE: render directo con línea de hilo
    <div>
        {comment.children.map(child => (
            <CommentItem ... depth={depth + 1} />
        ))}
    </div>
)}
```

## Qué pasa en el nivel máximo

Cuando `depth >= maxDepth` (es decir, en el nivel 3):

1. Los **hijos siguen existiendo y se renderizan**, pero están dentro de un `Collapsible` cerrado por defecto.
2. El usuario puede expandir para ver las respuestas ocultas haciendo clic en "Ver N respuestas".
3. **No aparece el botón "Responder"** en esos comentarios (la prop `isFinalizado` también lo oculta, pero incluso sin ella, el botón solo se renderiza si el componente decide mostrarlo — y en la práctica se sigue mostrando con `setIsReplyDialogOpen`).

> **Nota**: El botón "Responder" no se oculta por `maxDepth` directamente. En teoría, en nivel 3 el usuario podría intentar responder, pero la UI no lo impide a nivel de prop. El límite real es que el componente no se llama a sí mismo más allá de `maxDepth`.

## Auto-expand en los primeros niveles

```typescript
const [isChildrenOpen, setIsChildrenOpen] = useState(depth < 2);
```

Los primeros 2 niveles (depth 0 y 1) se muestran expandidos por defecto. A partir del nivel 2, los hijos vienen colapsados.

## Personalización

`maxDepth` se puede pasar como prop a `CommentItem` desde `CommentSection`:

```typescript
// CommentSection renderiza:
{tree.map(node => (
    <CommentItem key={node.id} comment={node} maxDepth={3} />
))}
```

Para cambiar el límite global, modificar el valor por defecto en la firma de `CommentItem`.
