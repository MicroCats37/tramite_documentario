# ExpedienteViewModal

**Responsabilidad**: Modal de solo lectura (view-only) que muestra el detalle completo de un expediente, incluyendo datos del solicitante, documento, y flujo de gestión de la solicitud asociada. No permite edición.

**Ubicación**: `frontend/src/app/dashboard/expedientes/_components/ExpedienteViewModal.tsx`

---

## Props

```typescript
interface ExpedienteViewModalProps {
  expediente: Expediente | null;  // null = no renderiza nada
  isOpen: boolean;
  onClose: () => void;
}
```

---

## Estructura Visual

### Header

- **Ícono**: `<FileText>` sobre fondo con borde primario
- **Título**: `expediente.id_publico` (ej: "EXP-2026-00001")
- **Badge tipo documento**: `tipo_documento` formateado (underscores → espacios)
- **Badge persona**: "PERSONA JURÍDICA" (indigo) o "PERSONA NATURAL" (teal)
- **Badge estado solicitud**: Solo visible si existe solicitud, con color semántico
- **Tiempo transcurrido**: `formatDistanceToNow` con locale español

### Body (2 columnas si hay solicitud, 1 si no)

#### Columna 1: Base Documentaria

1. **Sección Solicitante**
   - Ícono dinámico: `<Building2>` o `<User>` según tipo persona
   - Nombre: `razon_social` (jurídica) o `apellidos, nombres` (natural)
   - Badge: RUC o DNI según corresponda
   - Contacto: Teléfono + Email en grid 2 columnas

2. **Sección Expediente**
   - Asunto (texto completo)
   - Grid de metadatos: N° documento, folios, fecha registro, expediente CIP
   - Archivos:
     - Archivo principal con link externo
     - Anexos con link y descripción

#### Columna 2: Gestión del Trámite (solo si existe solicitud)

- **Badge ID solicitud**: `solicitud.id_publico`
- **Estado actual**: Badge grande con ícono y color semántico
- **Timeline vertical**:
  - Inicio del trámite (fecha creación expediente)
  - Fecha límite (si existe)
- **Equipo responsable**:
  - Avatar del asignado principal con nombre
  - Avatares de colaboradores con tooltips

### Footer

- **Cerrar**: Botón outline
- **Ver Detalles Completos**: Link a `/dashboard/expedientes/{id}` con ícono `<FileText>`

---

## Configuración de Estados (Helper)

```typescript
const getEstadoConfig = (estado: string) => {
  switch (estado?.toUpperCase()) {
    case "EN_GESTION_MP":
      return { color: "bg-orange-50 text-orange-700 border-orange-200", icon: Timer };
    case "EN_PROCESO":
      return { color: "bg-primary/5 text-primary border-primary/20", icon: Clock };
    case "COMPLETADA":
      return { color: "bg-emerald-50 text-emerald-700 border-emerald-200", icon: CheckCircle2 };
    case "OBSERVADA":
      return { color: "bg-red-50 text-red-700 border-red-200", icon: AlertCircle };
    default:
      return { color: "bg-slate-100 text-slate-700 border-slate-200", icon: AlertCircle };
  }
};
```

---

## Helpers Visuales (Componentes Internos)

### `SectionTitle`
```typescript
const SectionTitle = ({ title, icon: Icon }: { title: string; icon: any }) => (
  <div className="flex items-center gap-2 mb-4 pb-2 border-b border-primary/10">
    <div className="p-1.5 bg-primary/10 rounded-md text-primary shrink-0">
      <Icon className="w-4 h-4" />
    </div>
    <h4 className="text-sm font-bold text-foreground/80 uppercase tracking-wide truncate">
      {title}
    </h4>
  </div>
);
```

### `DetailRow`
```typescript
const DetailRow = ({ label, value, className = "" }) => (
  <div className={`flex flex-col gap-1 min-w-0 ${className}`}>
    <span className="text-[10px] uppercase font-bold text-muted-foreground/70 tracking-wider truncate">
      {label}
    </span>
    <span className="text-sm font-medium text-foreground break-words leading-tight">
      {value || <span className="italic text-muted-foreground/40">--</span>}
    </span>
  </div>
);
```

### `UserInfo`
```typescript
const UserInfo = ({ user, label }: { user: any; label: string }) => {
  // Avatar con iniciales + nombre + área
  // Retorna null si !user
};
```

---

## Tipos de Persona

```typescript
const isJuridica = expediente.tipo_persona === "JURIDICA";
// Determina qué campos mostrar:
// - JURIDICA: razon_social, ruc
// - NATURAL: apellidos + nombres, dni
```

---

## Notas de Implementación

- **Solo lectura**: No hay props de `onSave` ni handlers de edición.
- **Grid responsive**: 1 columna mobile, 2 columnas en `lg` cuando hay solicitud.
- **Null guard**: Si `expediente` es `null`, retorna `null` (no renderiza nada).
- **Tooltips**: Para colaboradores usando `TooltipProvider` de shadcn/ui.
- **Links externos**: Archivo principal y anexos usan `target="_blank"`.
- **Overflow**: El body tiene `overflow-y-auto` con `min-h-0` para flexibilidad.
