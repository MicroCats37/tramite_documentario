# Page Detalle — Solicitud Individual

## Componente: `SolicitudDetailPage`

**Ubicación**: `src/app/dashboard/solicitudes/[id]/page.tsx`

Página de detalle de una sola solicitud. Es un componente de cliente (`"use client"`) que consume el hook `useFetchSolicitudById`.

---

## Obtención de ID desde Params

```typescript
const params = useParams();
const solicitudId = Array.isArray(params.id) ? params.id[0] : params.id;
```

- **Normalización**: `params.id` puede ser string o array. Se normaliza a string.

---

## Fetching de Datos

```typescript
const {
  data: solicitud,
  isLoading,
  isError,
} = useFetchSolicitudById(solicitudId);
```

El hook `useFetchSolicitudById`:
- Query key: `["solicitudes", "detail", id]`
- URL: `/api/solicitudes/{id}/`
- Schema: `SolicitudCardSchema`
- Retry: 2 intentos, pero no reintenta en 404.

---

## Estados de Carga y Error

```typescript
if (isLoading)
  return <div className="p-8 flex justify-center text-muted-foreground">Cargando solicitud...</div>;

if (isError || !solicitud)
  return <div className="p-8 text-destructive">Error al cargar la solicitud.</div>;
```

---

## Layout: Grid de 2 Columnas

```typescript
<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
  {/* Columna Izquierda (2/3) */}
  <div className="lg:col-span-2 space-y-6">
    {/* Expediente Vinculado */}
    {/* Evidencia Anexada */}
    {/* Historial de Comentarios */}
  </div>

  {/* Columna Derecha (1/3) */}
  <div className="space-y-6">
    {/* Plazos y Fechas */}
    {/* Personal Asignado */}
  </div>
</div>
```

---

## Columna Izquierda (Contenido Principal)

### 1. Expediente Vinculado

Card con borde azul izquierdo (`border-l-4 border-l-blue-500`). Muestra:
- `expediente.id_publico` con link al expediente
- `expediente.nombres` + `expediente.apellidos`
- Botón "Ver Expediente" que linkea a `/dashboard/expedientes/{id}`

### 2. Evidencia Anexada

Itera sobre `solicitud.anexos`. Cada archivo muestra:
- Icono de documento
- Descripción o "Sin descripción"
- Fecha de creación formateada
- Link de descarga (`archivo_anexo`)

Si no hay anexos: mensaje en italic "No hay archivos de evidencia adjuntos."

### 3. Historial de Comentarios

Card con `Badge` que muestra el conteo de comentarios:
```typescript
<Badge variant="secondary" className="ml-auto">
  {solicitud.comentarios.length}
</Badge>
```

Usa `CommentThread` envuelto en `ScrollArea` para overflow controlado.

---

## Columna Derecha (Metadatos)

### Plazos y Fechas

Determina si está vencida:
```typescript
const isVencida = solicitud.fecha_limite
  ? new Date(solicitud.fecha_limite) < new Date()
  : false;
```

- Color del borde superior: rojo si `isVencida`, verde si no.
- Muestra `fecha_límite` formateada + tiempo relativo (`formatDistanceToNow`).
- Badge "Vencido" si está vencida y no finalizada.
- Fechas de actualización y cierre.

### Personal Asignado

Muestra:
- **Responsable Principal**: Avatar con iniciales + nombre completo + username + email.
- **Última Modificación**: Nombre de `modificado_por`.
- **Usuarios Adjuntados**: Tags con username de cada usuario adjuntado.

---

## Badges de Estado

```typescript
const getEstadoBadgeColor = (estado: string) => {
  if (estado.includes("FINALIZADO") || estado.includes("CERRADO"))
    return "bg-green-100 text-green-700 border-green-200";
  if (estado.includes("RECHAZADO") || estado.includes("OBSERVADO"))
    return "bg-red-100 text-red-700 border-red-200";
  if (estado.includes("EN_GESTION"))
    return "bg-blue-100 text-blue-700 border-blue-200";
  return "bg-slate-100 text-slate-700 border-slate-200";
};
```

Lógica por palabras clave en el estado (no por valor exacto del enum).

---

## Navegación

- Botón "Volver" con `router.back()` para regresar a la página anterior.
- Breadcrumb: `Volver / Detalle de Solicitud`.

---

## Resumen de Composición

```
SolicitudDetailPage
├── Header (Volver + Título + Badge Estado)
└── Grid 3 cols
    ├── Col Izquierda (2/3)
    │   ├── Card: Expediente Vinculado
    │   ├── Card: Evidencia Anexada (map sobre anexos)
    │   └── Card: Comentarios (CommentThread + ScrollArea)
    └── Col Derecha (1/3)
        ├── Card: Plazos y Fechas
        └── Card: Personal Asignado
```
