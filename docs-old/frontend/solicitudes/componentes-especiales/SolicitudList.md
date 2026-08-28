# SolicitudList

Componente **presentacional puro**. Recibe el estado final de los datos y callbacks de paginación; no tiene acceso directo a hooks de fetch.

## Rol en la Arquitectura

- **Presentational component**: según el patrón container/presentational de React.
- **Solo lee props**: no consume contextos, no hace fetching, no maneja estado de modales.

## Props

```typescript
interface SolicitudListProps {
  user: LoginUserData;
  data: SolicitudCardType[];        // Array de solicitudes ya fetcheadas
  isLoading: boolean;
  error: Error | null;
  currentPage: number;
  totalPages: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
}
```

## Estados Visuales (orden de precedencia)

| Condición | Render |
|-----------|--------|
| `isLoading === true` | Spinner centrado con mensaje "Cargando solicitudes..." |
| `error !== null` | Card de error con mensaje destructivo |
| `totalItems === 0` | Card vacía con sugerencia de cambiar filtros |
| Caso normal | Grid de `SolicitudCard` + paginación |

## Estructura de Render

```
SolicitudList
├── Loading state  (if isLoading)
├── Error state   (if error)
├── Empty state   (if totalItems === 0)
└── Normal state
    ├── SolicitudCard[]  (grid 1 columna)
    └── Pagination control  (solo si totalPages > 1)
```

## Paginación

- Offset calculado: `(currentPage - 1) * pageSize`
- Controles: ChevronLeft, ChevronRight + display "X / Y"
- Botones deshabilitados en extremos (`currentPage <= 1`, `currentPage >= totalPages`)

## Dependencias

- `lucide-react`: `ChevronLeft`, `ChevronRight`, `Frown`, `Loader2`
- `@/components/ui/button`, `@/components/ui/card`
- `./SolicitudCard`: componente hijo que maneja sus propios modales
