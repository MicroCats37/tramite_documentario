# Vista: Page Detalle — Expedientes

## Archivo Principal

**Ruta**: `frontend/src/app/dashboard/expedientes/[id]/page.tsx`

**Componente**: `ExpedienteDetailPage` (export default)

---

## Layout: Grid 4+8 Columnas

### Estructura de Grid

```typescript
// Bootstrap-style 12-column grid
<div className="grid grid-cols-12 gap-6 md:gap-8">

  {/* Columna IZQUIERDA — 4 columnas (lg:col-span-4) */}
  <div className="col-span-12 lg:col-span-4">
    <!-- Información de Origen (estático) -->
  </div>

  {/* Columna DERECHA — 8 columnas (lg:col-span-8) */}
  <div className="col-span-12 lg:col-span-8">
    <!-- Flujo de Solicitud (dinámico) -->
  </div>

</div>
```

### Columna Izquierda (4 cols) — Información de Origen

Contiene 2 Cards estáticos con datos del expediente:

#### Card 1: Datos del Solicitante
- Tipo de persona (Natural/Jurídica) → muestra campo correcto
- DNI o RUC según tipo
- Correo electrónico
- Teléfono

#### Card 2: Detalles del Documento
- Tipo de documento
- Número de folios
- Asunto
- Link al PDF original (si existe)

### Columna Derecha (8 cols) — Flujo de Trabajo

Contenido **dinámico** que cambia según si existe `solicitud`:

| Estado | Contenido |
|--------|-----------|
| **CON solicitud** | Ficha de datos vitales, Evidencias/Anexos, Historial de conversación |
| **SIN solicitud** | Card con estado "vacío" y CTA para iniciar flujo |

---

## Obtención del ID

```typescript
// URL: /dashboard/expedientes/[id] → params.id = "123"
const params = useParams();
const expedienteId = Array.isArray(params.id) ? params.id[0] : (params.id as string);

// Uso en query
const { data: expediente, isLoading, error } = useFetchExpedienteById(expedienteId);
```

**Validaciones**:
- `Array.isArray` — maneja caso edge donde Next.js puede retornar array
- `!!id` en `enabled` del query — no ejecuta si ID está vacío

---

## Obtención de Datos (useFetchExpedienteById)

```typescript
const useFetchExpedienteById = (id: string | number) => {
  return useApiQuery({
    queryKey: [...EXPEDIENTES_QUERY_KEY, "detail", id],
    url: `/api/expedientes/${id}/`,
    schema: ExpedienteSchema,
    queryOptions: {
      staleTime: 1000 * 60 * 30,  // 30 minutos
      enabled: !!id,               // Solo si hay ID
    },
  });
};
```

---

## Datos que Cruza (Relaciones)

### Expediente → Solicitud

```typescript
const isJuridica = expediente.tipo_persona === "JURIDICA";
const solicitud = expediente.solicitud;
const hasSolicitud = !!solicitud;
```

### Datos del Solicitante (Renderizado Condicional)

```typescript
{isJuridica
  ? expediente.razon_social
  : `${expediente.nombres} ${expediente.apellidos}`
}
```

### Campos mostrados según tipo de persona

| Campo | Natural | Jurídica |
|-------|---------|----------|
| Identificación | `dni` | `ruc` |
| Nombre | `nombres + apellidos` | `razon_social` |

### Solicitud — Estados Visuales

```typescript
const getStatusConfig = (status: string) => {
  switch (status?.toUpperCase()) {
    case "EN_GESTION_MP": return { bg: "bg-orange-100", text: "text-orange-700", icon: Timer };
    case "EN_PROCESO": return { bg: "bg-blue-100", text: "text-blue-700", icon: Clock };
    case "COMPLETADA": return { bg: "bg-emerald-100", text: "text-emerald-700", icon: CheckCircle2 };
    default: return { bg: "bg-slate-100", text: "text-slate-700", icon: FileText };
  }
};
```

### Usuario Actual (Auth)

```typescript
const [user, setUser] = useState<LoginUserData | undefined>(undefined);

useEffect(() => {
  getUserCookie().then(setUser).catch(() => {});
}, []);
```

---

## Subcomponentes Integrados

### CommentSection

```typescript
<CommentSection
  comentarios={solicitud.comentarios}
  solicitudId={String(solicitud.id)}
  expedienteId={String(expediente.id)}
  isFinalizado={solicitud.finalizado}
  variant="page"
  showHeader={false}
/>
```

**Props**:
- `comentarios` — array de comentarios de la solicitud
- `solicitudId` — ID de la solicitud (para mutations)
- `expedienteId` — ID del expediente (contexto)
- `isFinalizado` — boolean que puede deshabilitar interacción
- `variant="page"` — indica que se renderiza en page full
- `showHeader={false}` — header ya está en Card wrapper

### ModalSolicitudForm

```typescript
<ModalSolicitudForm
  currentUser={user!}
  isOpen={isModalSolicitudOpen}
  onClose={() => setIsModalSolicitudOpen(false)}
  solicitud={expediente?.solicitud}
  expediente={expediente}
  onSave={handleSaveSolicitud}
  isLoading={SolicitudcreateMutation.isPending || SolicitudupdateMutation.isPending}
/>
```

---

## Lógica de Guardado (handleSaveSolicitud)

```typescript
const handleSaveSolicitud = async (data: SolicitudCreateFormData | SolicitudUpdateFormData) => {
  if (expediente && !expediente.solicitud) {
    // NO existe solicitud → CREAR
    await SolicitudcreateMutation.mutateAsync(data as SolicitudCreateFormData);
  } else if (expediente?.solicitud) {
    // YA existe solicitud → ACTUALIZAR
    await SolicitudupdateMutation.mutateAsync({
      id: expediente.solicitud.id,
      data: data as SolicitudUpdateFormData
    });
  }
  setIsModalSolicitudOpen(false);
};
```

---

## Helpers Visuales

### DetailRow

```typescript
const DetailRow = ({ label, value, icon: Icon }: any) => (
  <div className="space-y-1">
    <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
      {Icon && <Icon className="w-3 h-3" />}
      {label}
    </p>
    <p className="text-sm font-medium text-foreground wrap-break-word leading-snug">
      {value || <span className="italic text-muted-foreground/40">--</span>}
    </p>
  </div>
);
```

### UserBadge

```typescript
const UserBadge = ({ user, role, color = "bg-slate-100" }: any) => {
  // Muestra avatar con iniciales + nombre + rol
  // Retorna "No asignado" si user es null
};
```

---

## Estados de Carga y Error

```typescript
if (isLoading) {
  return <div className="p-8 animate-pulse space-y-4">
    <div className="h-12 bg-muted rounded-lg w-full" />
    <div className="h-64 bg-muted rounded-lg w-full" />
  </div>;
}

if (error || !expediente) {
  return <div className="p-20 text-center">
    <Button onClick={() => router.back()}>Volver</Button>
  </div>;
}
```

---

## Iconografía (Lucide Icons)

| Icon | Uso |
|------|-----|
| `ArrowLeft` | Botón volver |
| `FileSearch` | Header "Información de Origen" |
| `User` | Datos del solicitante |
| `Hash` | DNI/RUC |
| `Mail` | Correo |
| `Phone` | Teléfono |
| `FileText` | Detalles documento |
| `Layers` | Folios |
| `ExternalLink` | Link PDF |
| `Activity` | Seguimiento |
| `Timer` | Tiempo/Fecha límite |
| `Calendar` | Fecha inicio |
| `CheckCircle2` | Estado completada |
| `Clock` | Estado en proceso |
| `Paperclip` | Anexos |
| `Download` | Descargar anexo |
| `MessageSquare` | Historial conversación |
| `Briefcase` | Gestionar flujo |
| `Send` | Iniciar trámite |
