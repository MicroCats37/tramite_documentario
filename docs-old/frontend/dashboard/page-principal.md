# Página Principal del Dashboard

## Vista General

La página principal (`/dashboard`) es un componente **Client** que muestra un panel de control con KPIs y una lista de actividad reciente. Se implementa en `src/app/dashboard/page.tsx`.

```
┌─────────────────────────────────────────────────────────────┐
│  Panel de Control                                           │
│  Resumen de tus actividades pendientes                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Total       │  │ Mis         │  │ Colabora-   │         │
│  │ Pendientes  │  │ Asignaciones│  │ ciones      │         │
│  │     3       │  │     2       │  │     1       │         │
│  │Solicitudes  │  │ Soy respon- │  │Estoy        │         │
│  │  activas    │  │ sable       │  │adjunto      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  Solicitudes Pendientes              Ver todas →           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ EXP-2024-001    [Asignado]    Ver Solicitud         │   │
│  │ EXP-2024-002    [Asignado]    Ver Solicitud         │   │
│  │ EXP-2024-003    [Colaborador] Ver Solicitud         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## El Hook `useMisPendientes`

### Definición

Ubicación: `src/hooks/solicitudes/useMisPendientes.tsx`

```tsx
export const useMisPendientes = () => {
  return useApiQuery<MisPendientesResponse>({
    queryKey: ["mis-pendientes"],
    url: "api/pendientes/",
    schema: MisPendientesResponseSchema,
    queryOptions: {
      refetchOnWindowFocus: false,
    },
  });
};
```

### Cómo funciona

1. **Wrapea `useApiQuery`**: hook genérico de React Query que maneja fetching, caché y errores
2. **Cache key**: `["mis-pendientes"]` — React Query usa esto para evitar re-fetching innecesario
3. **Endpoint**: `GET /api/pendientes/`
4. **Validación**: `MisPendientesResponseSchema` valida la respuesta con Zod
5. **Opciones**: `refetchOnWindowFocus: false` — no refresca automáticamente al cambiar de pestaña

### Respuesta esperada (`MisPendientesResponse`)

```typescript
interface MisPendientesResponse {
  solicitud_asignado: {
    cantidad: number;
    detalle: Array<{
      id_expediente: number;
      expediente_id_publico: string;
      // ... otros campos
    }>;
  };
  solicitudes_adjuntadas: {
    cantidad: number;
    detalle: Array<{ ... }>;
  };
}
```

- **`solicitud_asignado`**: solicitudes donde el usuario actual es el responsable
- **`solicitudes_adjuntadas`**: solicitudes donde el usuario es colaborador/adjunto

---

## KPIs (Key Performance Indicators)

La página muestra **3 tarjetas de resumen**:

### 1. Total Pendientes

```tsx
<Card className="p-6 border-l-4 border-l-primary hover:shadow-md">
  <p className="text-sm font-medium text-muted-foreground">Total Pendientes</p>
  <p className="text-2xl font-bold text-foreground">{totalPendientes}</p>
  <p className="text-xs text-muted-foreground">Solicitudes activas</p>
</Card>
```

- **Border izquierdo**: color primario de la app
- **Icono**: `<Inbox>` de Lucide en fondo `primary/10`
- **Valor**: suma de `asignadas + adjuntadas`

### 2. Mis Asignaciones

```tsx
<Card className="p-6 border-l-4 border-l-cip-gold">
  <p className="text-sm font-medium text-muted-foreground">Mis Asignaciones</p>
  <p className="text-2xl font-bold text-foreground">{asignadas.cantidad}</p>
  <p className="text-xs text-muted-foreground">Soy el responsable</p>
</Card>
```

- **Border izquierdo**: color `cip-gold` (dorado CIP)
- **Icono**: `<FileText>` en fondo `cip-gold/10`
- **Significado**: solicitudes donde el usuario tiene rol de responsable

### 3. Colaboraciones

```tsx
<Card className="p-6 border-l-4 border-l-slate-500">
  <p className="text-sm font-medium text-muted-foreground">Colaboraciones</p>
  <p className="text-2xl font-bold text-foreground">{adjuntas.cantidad}</p>
  <p className="text-xs text-muted-foreground">Estoy adjunto</p>
</Card>
```

- **Border izquierdo**: gris slate
- **Icono**: `<Users>` en fondo `slate-500/10`
- **Significado**: solicitudes donde el usuario está como colaborador

---

## Lista de Actividad Reciente

### Construcción de la lista

```tsx
const actividadReciente = [
  ...asignadas.detalle.map((item) => ({ ...item, tipo: "Asignado" })),
  ...adjuntas.detalle.map((item) => ({ ...item, tipo: "Colaborador" })),
].slice(0, 5);
```

Combina ambas listas y les agrega un campo `tipo` ("Asignado" o "Colaborador"), luego limita a los primeros 5 items.

### Renderizado de cada item

```tsx
<div className="flex items-center justify-between py-3 border-b hover:bg-muted/50">
  <Link href={`/dashboard/expedientes/${item.id_expediente}`}>
    {item.expediente_id_publico}
  </Link>

  <div className="flex items-center gap-3">
    <span className={`px-3 py-1 text-xs font-medium rounded-full ${
      item.tipo === "Asignado"
        ? "bg-cip-gold/10 text-cip-gold-dark border border-cip-gold/20"
        : "bg-slate-100 text-slate-700 border border-slate-200"
    }`}>
      {item.tipo}
    </span>

    <Link href={`/dashboard/expedientes/${item.id_expediente}`}>
      Ver Solicitud
    </Link>
  </div>
</div>
```

- **Enlace al expediente**: `#expediente-{id}` → lleva a la vista del expediente
- **Badge de tipo**: dorado para "Asignado", gris para "Colaborador"
- **Botón "Ver Solicitud"**: mismo enlace, estilo de botón secundario

### Estados de la lista

| Estado | Condición | UI |
|--------|-----------|-----|
| Cargando | `isLoading` | "Cargando tablero..." |
| Error | `isError \|\| !data` | "Error al cargar datos del tablero." |
| Vacía | `actividadReciente.length === 0` | "No tienes solicitudes pendientes." |
| Con datos | default | Lista de items |

---

## Estados de Carga y Error

```tsx
if (isLoading) {
  return <div className="p-6">Cargando tablero...</div>;
}

if (isError || !data) {
  return (
    <div className="p-6 text-red-500">Error al cargar datos del tablero.</div>
  );
}
```

El componente delega el manejo de loading y error a `useMisPendientes`, que usa `useApiQuery` internamente. Los estados de React Query (`isLoading`, `isError`) se mapean directamente a la UI.

---

## Optimización: Carga en el Shell

Un detalle arquitectónico importante: `useMisPendientes` se llama en **dos lugares**:

1. **`DashboardShell`** — para el badge del sidebar
2. **`DashboardPage`** — para los KPIs

Gracias a la caché de React Query, cuando `DashboardPage` se monta, los datos ya están disponibles en caché. El segundo `useMisPendientes` retorna los datos inmediatamente sin hacer una nueva petición:

```
┌──────────────────────────────────────────────────────────────┐
│                        TIMELINE                              │
│                                                              │
│  [DashboardShell se monta] ──→ useMisPendientes()            │
│                                      │                       │
│                                      ↓                       │
│                              [Fetch /api/pendientes/]        │
│                                      │                       │
│                                      ↓                       │
│                              [Datos en caché]                │
│                                                              │
│  [DashboardPage se monta] ──→ useMisPendientes()             │
│                                      │                       │
│                                      ↓                       │
│                              [Datos de caché INSTANTÁNEO]   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

Esto evita una segunda llamada a la API y hace que la página cargue al instante.
