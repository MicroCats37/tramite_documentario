# ModalCrearSolicitud

Modal de creación y edición de solicitudes. Componente **presentacional** que recibe datos y callbacks via props; toda la lógica de negocio vive en el padre o en `SolicitudForm`.

## Rol en la Arquitectura

- **Pure UI wrapper**: encapsula el `Dialog` de Radix UI y delega el formulario a `SolicitudForm`.
- **Bidi-reccional**: sirve tanto para crear una solicitud nueva (asociada a un expediente) como para editar una existente.

## Props

```typescript
interface SolicitudModalProps {
  isOpen: boolean;                               // Control de visibilidad
  onClose: () => void;                           // Callback de cierre
  currentUser: LoginUserData;                   // Usuario autenticado
  expediente: { id: string; id_publico: string } | null;  // Expediente base (crear)
  solicitud?: Solicitud | null;                   // Solicitud existente (editar)
  onSave: (data: SolicitudUpdateFormData) => Promise<void>;  // Handler de guardado
  isLoading?: boolean;                           // Estado de carga del submit
}
```

## Decisión Crear vs. Editar

```typescript
const isEditing = !!solicitud;
const title = isEditing
  ? `Editar Solicitud ${solicitud.id_publico || ""}`
  : `Nueva Solicitud - Expediente ${expediente?.id_publico || ""}`;
```

- Si `solicitud` tiene valor → modo edición
- Si `expediente` tiene valor → modo creación

## Manejo de Errores

```typescript
const handleSave = async (formData) => {
  try {
    await onSave(formData);
    onClose();
  } catch (error) {
    console.error("Error", error);
    throw error; // Re-lanza para que el form lo capture
  }
};
```

El error se re-lanza al `SolicitudForm` para su manejo in-formulario (validación, display de errores).

## Estados del Diálogo

| Estado | Comportamiento |
|--------|----------------|
| `open=true` | Muestra `DialogContent` con `max-h-[90vh] overflow-y-auto` |
| `open=false` (por usuario) | Dispara `onClose()` |
| Submit exitoso | `onClose()` cierra el modal |
| Submit en error | Se mantiene abierto, el form muestra el error |

## Dependencias

- `@/components/ui/dialog`: `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`
- `./forms/SolicitudForm`: Formulario interno que maneja campos y validación Zod
