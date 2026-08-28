# ModalCrearExpediente

**Responsabilidad**: Wrapper de Dialog que encapsula el formulario de expediente. Gestiona el ciclo de vida del modal: apertura, cierre, y coordinación del guardado con el padre. Delega toda la lógica de formulario a `ExpedienteForm`.

**Ubicación**: `frontend/src/app/dashboard/expedientes/_components/modal/ModalCrearExpediente.tsx`

---

## Props

```typescript
interface ExpedienteModalProps {
  isOpen: boolean;
  onClose: () => void;
  expediente?: Expediente | null;  // null/undefined = modo crear
  onSave: (data: ExpedienteCreateFormData | ExpedienteUpdateFormData) => Promise<void>;
  isLoading?: boolean;              // default: false
}
```

### Props detalladas

| Prop | Tipo | Requerido | Descripción |
|------|------|-----------|-------------|
| `isOpen` | `boolean` | Sí | Controla la apertura del Dialog |
| `onClose` | `() => void` | Sí | Callback para cerrar desde el hijo |
| `expediente` | `Expediente \| null \| undefined` | No | `null/undefined` = modo crear; `Expediente` = modo editar |
| `onSave` | `function` | Sí | Función async del padre que ejecuta la mutación |
| `isLoading` | `boolean` | No | Flag de loading para deshabilitar el formulario |

---

## Título y Descripción Dinámicos

```typescript
// Modo crear
<DialogTitle>Crear Nuevo Expediente</DialogTitle>
<DialogDescription>
  Complete la información para registrar un nuevo expediente en el sistema.
</DialogDescription>

// Modo editar
<DialogTitle>Editar Expediente {expediente.id_publico}</DialogTitle>
<DialogDescription>
  Modifique los datos necesarios del expediente existente.
</DialogDescription>
```

---

## Control de Cierre y Guardado

### Flujo de Guardado

```
User hace submit en ExpedienteForm
  → handleSave(data) en ModalExpedienteForm
    1. await onSave(data)          ← Llama al padre (puede lanzar error)
    2. onClose()                   ← Solo si onSave succeeds
    catch (error):
      → console.error(error)
      → NO llama onClose()        ← Modal permanece abierto para corregir
```

### Puntos Clave

1. **Cierre condicional**: El modal solo se cierra si `onSave` no lanza error.
2. **Error handling**: El error se loguea pero no se re-lanza — el padre es responsable de manejarlo (ShellExpedientes sí re-lanza para su chain flow).
3. **onClose via Dialog**: `onOpenChange` del Dialog llama a `onClose` cuando el usuario hace click fuera o presiona Escape.

---

## Estructura JSX

```tsx
<Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
  <DialogContent className="sm:max-w-[900px] max-h-[90vh] overflow-y-auto">
    <DialogHeader>
      <DialogTitle>{expediente ? `Editar...` : 'Crear...'}</DialogTitle>
      <DialogDescription>...</DialogDescription>
    </DialogHeader>
    <ExpedienteForm
      expediente={expediente || null}
      onSave={handleSave}
      onCancel={onClose}
      isLoading={isLoading}
    />
  </DialogContent>
</Dialog>
```

---

## Comportamiento del Dialog

- **Click fuera**: Cierra el modal (invoca `onClose`)
- **Tecla Escape**: Cierra el modal (invoca `onClose`)
- **Overflow**: `overflow-y-auto` permite scroll dentro del formulario si es necesario
- **Tamaño máximo**: `sm:max-w-[900px]` ancho, `max-h-[90vh]` alto

---

## Relación con ExpedienteForm

`ModalCrearExpediente` **no contiene lógica de formulario**. Solo:

1. Controla la apertura/cierre del Dialog
2. Pasa `handleSave` que envolverá la llamada a `onSave` del padre
3. Pasa `onClose` directamente como `onCancel` al formulario

El `ExpedienteForm` es responsable de:
- Renderizar campos del formulario
- Validación
- Estado de loading local
- Llamar a `onSave` o `onCancel`

---

## Estados del Modal

| Estado | Visual |
|--------|--------|
| Abierto modo crear | Título "Crear Nuevo Expediente", formulario vacío |
| Abierto modo editar | Título "Editar Expediente {id}", formulario pre-rellenado |
| Loading (`isLoading=true`) | Formulario deshabilitado, botón de submit muestra estado |
| Guardado exitoso | Se cierra el modal |
| Error en guardado | Modal permanece abierto, error logueado |

---

## Notas de Implementación

- **Wrapper minimalista**: El modal es un passthrough — toda la lógica está en `ExpedienteForm`.
- **Separación de responsabilidades**: `onSave` del padre recibe los datos ya validados por `ExpedienteForm`.
- **Prop drilling**: `isLoading` se pasa a través del modal hasta el formulario.
