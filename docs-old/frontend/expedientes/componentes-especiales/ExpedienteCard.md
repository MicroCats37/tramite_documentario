# ExpedienteCard

**Responsabilidad**: Componente de presentación que renderiza un expediente individual como una card. Muestra datos del solicitante, documento, solicitud asociada (si existe), y acciones disponibles. Es puramente presentacional — todas las acciones son callbacks al padre.

**Ubicación**: `frontend/src/app/dashboard/expedientes/_components/ExpedienteCard.tsx`

---

## Props

```typescript
interface ExpedienteCardProps {
  user: LoginUserData;
  expediente: Expediente;
  onView: (expediente: Expediente) => void;
  onEditExpediente: (expediente: Expediente) => void;
  onEditSolicitud: (expediente: Expediente) => void;
  currentUserId?: number;
}
```

### Props detalladas

| Prop | Tipo | Requerido | Descripción |
|------|------|-----------|-------------|
| `user` | `LoginUserData` | Sí | Usuario actual (para contexto) |
| `expediente` | `Expediente` | Sí | Datos del expediente a mostrar |
| `onView` | `function` | Sí | Callback: abrir modal de vista |
| `onEditExpediente` | `function` | Sí | Callback: abrir modal de edición expediente |
| `onEditSolicitud` | `function` | Sí | Callback: abrir modal de solicitud |
| `currentUserId` | `number` | No | ID del usuario actual (no usado en el componente) |

---

## Estructura Visual (6 Filas)

### Fila 1: ID, Identidad, Contacto

**Bloque 1 — ID y Tipo**
- Badge con `id_publico` (ej: "EXP-2026-00001")
- Tipo documento formateado debajo

**Bloque 2 — Identidad**
- Ícono `<Building2>` o `<User>` según `tipo_persona`
- Nombre: `razon_social` o `nombres + apellidos`
- Badge "JURÍDICA" (dorado) o "NATURAL" (gris)
- DNI/RUC debajo

**Bloque 3 — Contacto**
- Teléfono con ícono `<Phone>`
- Email con ícono `<Mail>`
- Folios con ícono `<Layers>`

### Fila 2: Asunto Expediente

```tsx
<div className="border rounded-md p-3 bg-background">
  <span className="text-[12px] font-bold uppercase tracking-wide block mb-1 text-muted-foreground">
    Asunto Expediente
  </span>
  <p className="text-[10px] font-medium text-foreground line-clamp-2">
    {expediente.asunto}
  </p>
</div>
```

### Fila 3: Archivos Expediente

- **Archivo principal**: Link con ícono `<FileText>`, texto "Principal"
- **Anexos**: Lista de links con `<Paperclip>` y descripción

### Fila 4: Fecha Creación Expediente

```
[Calendar icon] Creado: {createdDate}
[si diferente] [Clock icon] Modificado: {updatedDate}
```

### Fila 5: Solicitud (solo si existe)

Solo visible si `solicitud` no es null:

- **Header**: Ícono `<Briefcase>` + "Solicitud en Proceso" + Badge estado
- **Usuario asignado**: Avatar con iniciales + nombre + área
- **Fechas**: Inicio solicitud + Fecha límite (con alerta si vencida)
- **Estilo**: `border-2 border-primary/30 rounded-lg bg-primary/5`

### Fila 6: Acciones

| Botón | Condición | Acción |
|-------|-----------|--------|
| "Ver Detalle" | Siempre | `onView(expediente)` |
| Comentarios | Solo si hay solicitud | Abre `ModalComentariosSolicitud` |
| Menú (⚙️) | Siempre | Dropdown con opciones |

**Dropdown Menu:**
```tsx
<DropdownMenuContent align="end">
  {!solicitud && (
    <DropdownMenuItem onClick={() => onEditExpediente(expediente)}>
      <Edit className="w-4 h-4 mr-2" /> Editar Expediente
    </DropdownMenuItem>
  )}
  <DropdownMenuItem onClick={() => onEditSolicitud(expediente)}>
    <Briefcase className="w-4 h-4 mr-2" />
    {solicitud ? "Administrar Solicitud" : "Crear Solicitud"}
  </DropdownMenuItem>
</DropdownMenuContent>
```

---

## Helpers Visuales

### `LabelValue`
```typescript
const LabelValue = ({ label, value, icon: Icon, className = "", highlight = false }) => (
  <div className={`flex flex-col gap-0.5 ${className}`}>
    <span className="text-[10px] font-bold text-muted-foreground/70 uppercase tracking-wider flex items-center gap-1.5 opacity-90">
      {Icon && <Icon className="w-3 h-3" />} {label}
    </span>
    <span className={`text-xs font-semibold truncate block ${highlight ? "text-foreground" : "text-slate-700"}`}>
      {value || <span className="opacity-40 text-[10px] italic font-normal">--</span>}
    </span>
  </div>
);
```

### `UserBadge`
```typescript
const UserBadge = ({ user }: { user: any }) => {
  // Avatar circular con iniciales + nombre + área
  // Retorna "Sin asignar" si !user
};
```

---

## Lógica de Color de Estado

```typescript
const getStatusColor = (status: string) => {
  if (!status) return "bg-slate-100 text-slate-700";
  switch (status) {
    case "COMPLETADA":
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    case "EN_PROCESO":
      return "bg-slate-50 text-slate-700 border-slate-200";
    case "EN_GESTION_MP":
      return "bg-cip-red/10 text-cip-red border-cip-red/20";
    case "OBSERVADA":
      return "bg-cip-gold/10 text-cip-gold-dark border-cip-gold/20";
    default:
      return "bg-slate-50 text-slate-700 border-slate-200";
  }
};
```

---

## Lógica de Fecha Límite

```typescript
const limitDate = solicitud?.fecha_limite
  ? new Date(solicitud.fecha_limite)
  : null;
const isOverdue =
  limitDate && limitDate < new Date() && !solicitud?.finalizado;
// Si vencida: borde rojo, fondo rojo claro, ícono AlertTriangle
```

---

## Estado Local

```typescript
const [isCommentModalOpen, setIsCommentModalOpen] = useState(false);
```
Usado únicamente para el modal de comentarios (Dialog de shadcn/ui).

---

## Dependencias de UI

- **Badges**: shadcn/ui `Badge`
- **Buttons**: shadcn/ui `Button`
- **Card**: shadcn/ui `Card`
- **Dropdown**: shadcn/ui `DropdownMenu`
- **Tooltip**: shadcn/ui `Tooltip` (para colaboradores)
- **Dialog**: shadcn/ui `Dialog` + `DialogTrigger`
- **Separator**: shadcn/ui `Separator`
- **Icons**: lucide-react

---

## Notas de Implementación

- **No mutations**: Solo dispara callbacks — no ejecuta queries ni mutations.
- **Self-contained**: El modal de comentarios (`ModalComentariosSolicitud`) se renderiza dentro del Dialog del card.
- **Hover effects**: `hover:shadow-md hover:border-primary/40` en el Card padre.
- **Responsive**: Usa `flex-wrap` para adaptarse a diferentes anchos.
- **Persona jurídica**: Usa tokens `cip-gold` para colores distintivos.
