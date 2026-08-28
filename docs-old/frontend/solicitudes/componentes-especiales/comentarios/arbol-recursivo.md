# Árbol Recursivo de Comentarios

## Conversión de lista plana a árbol

La API devuelve los comentarios como una **lista plana**: cada comentario tiene un `parent` que es el ID del comentario padre (o `null` si es raíz). `buildCommentTree` transforma esa lista en una estructura jerárquica.

### Algoritmo (`buildCommentTree.ts`)

```typescript
export function buildCommentTree(flatComments: ComentarioType[]): CommentNode[] {
    const map: Record<string, CommentNode> = {};
    const tree: CommentNode[] = [];

    // 1. Crear un mapa[id] = nodo con children=[]
    flatComments.forEach((comment) => {
        map[String(comment.id)] = { ...comment, children: [] };
    });

    // 2. Recorrer y asignar cada nodo a su padre
    flatComments.forEach((comment) => {
        const parentId = comment.parent ? String(comment.parent) : null;
        if (parentId && map[parentId]) {
            map[parentId].children.push(map[String(comment.id)]);
        } else {
            tree.push(map[String(comment.id)]); // Es raíz
        }
    });

    // 3. Ordenar recursivamente por fecha (más recientes primero)
    sortRecursive(tree);
    return tree;
}
```

### Resultado

Entrada (plana):
```
{id: 1, texto: "Comentario raíz"}
{id: 2, texto: "Respuesta a 1", parent: 1}
{id: 3, texto: "Otra raíz"}
{id: 4, texto: "Respuesta a 2", parent: 2}
```

Salida (árbol):
```
[
  { id: 1, texto: "Comentario raíz", children: [
    { id: 2, texto: "Respuesta a 1", parent: 1, children: [
      { id: 4, texto: "Respuesta a 2", parent: 2, children: [] }
    ]}
  ]},
  { id: 3, texto: "Otra raíz", children: [] }
]
```

## Renderizado recursivo en `CommentItem`

`CommentItem` es el componente que se renderiza a sí mismo para cada nivel de profundidad:

```typescript
export function CommentItem({ comment, depth = 0, maxDepth = 3, ... }) {
    return (
        <>
            {/* 1. Render del comentario actual */}
            <div className="comment-body">...</div>

            {/* 2. Si tiene hijos → renderizar cada hijo recursivamente */}
            {hasChildren && (
                <div className="children">
                    {comment.children.map((child) => (
                        <CommentItem
                            key={child.id}
                            comment={child}
                            depth={depth + 1}    // increments
                            maxDepth={maxDepth}  // passed through
                            {...}
                        />
                    ))}
                </div>
            )}
        </>
    );
}
```

### Propagación de `maxDepth`

`maxDepth` se pasa como prop a cada `CommentItem` hijo sin alteración. Esto garantiza que el límite se aplique consistentemente en toda la rama del árbol, sin importar cuántos niveles haya.

## Tipos relacionados

```typescript
// Extiende ComentarioType con hijos
export interface CommentNode extends ComentarioType {
    children: CommentNode[];
}

// En ComentarioType (validations/solicitudes)
interface ComentarioType {
    id: string | number;
    texto: string;
    fecha_creacion: string;
    usuario: UsuarioType;
    parent?: string | number | null;  // ID del comentario padre
    anexos?: AnexoType[];
}
```
