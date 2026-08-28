# SolicitudCard

Card individual de una solicitud. **Stateful**: gestiona sus propios modales de edición y comentarios.

## Rol en la Arquitectura

- **Atomic/presentational**: representa una única solicitud con todas sus acciones posibles.
- **Auto-suficiente**: abre y cierra sus propios modales internamente.

## Estado Local

| Estado | Tipo | Inicial | Propósito |
|--------|------|---------|-----------|
| `isModalSolicitudOpen` | `boolean` | `false` | Modal de edición de solicitud |
| `isCommentModalOpen` | `boolean` | `false` | Modal de comentarios |

## Configuración de Estados (Map Estático)

`estadoConfig` es un record que mapea claves de estado a estilo visual:

```typescript
const estadoConfig: Record<string, { label, className, icon }> = {
  EN_GESTION_MP:   { label: "En Gestión MP",   className: "bg-cip-red/10 ...", icon: FileText },
  REENVIO_MP:      { label: "Reenvío a MP",     className: "bg-cip-red/20 ...", icon: Repeat2 },
  ENVIADO_A_AREA:  { label: "Enviado a Área",  className: "bg-cip-gold/10 ...", icon: Send },
  EN_TRAMITE_AREA: { label: "En Trámite",      className: "bg-slate-100 ...",  icon: Clock },
  CERRADO:         { label: "Cerrado",         className: "bg-slate-200 ...",  icon: Lock },
  COMPLETADA:      { label: "Completada",      className: "bg-emerald-50 ...",  icon: CheckCircle2 },
  DEFAULT:         { label: "Desconocido",      className: "bg-gray-50 ...",     icon: AlertCircle },
};
```

## Indicador de Borde Lateral (Estado Crítico)

```typescript
const borderClass = isOverdue
  ? "border-l-4 border-l-cip-red"        // Vencido
  : solicitud.finalizado
    ? "border-l-4 border-l-emerald-500"   // Finalizado
    : "border-l-4 border-l-cip-gold";     // En curso
```

## Lógica de Vencimiento

```typescript
const isOverdue = fechaLimite && fechaLimite < now && !solicitud.finalizado;
const daysLeft = fechaLimite ? differenceInDays(fechaLimite, now) : null;
```

- `isOverdue`: true solo si hay fecha_limite, ya venció, y NO está finalizado.
- `daysLeft`: positivo = días restantes, negativo = días vencido.

## Acciones Disponibles

| Acción | Componente | Tipo |
|--------|-----------|------|
| Ver Detalles | `Link` a `/dashboard/expedientes/{id}` | Navegación |
| Comentarios | `Dialog` + `ModalComentariosSolicitud` | Modal |
| Gestionar Solicitud | `Button` → `ModalSolicitudForm` | Modal |

## Mutación de Actualización

```typescript
const SolicitudupdateMutation = useUpdateSolicitud();
const handleSaveSolicitud = async (data) => {
  await SolicitudupdateMutation.mutateAsync({ id: solicitud.id, data });
};
```

- `isLoading` del modal se liga a `SolicitudupdateMutation.isPending`

## Avatares de Usuarios Adjuntados

- Máximo 3 avatares visibles
- Resto acumulado en `+N`
- Tooltip con nombre completo al hover

## Dependencias

- `@tanstack/react-query`: `useUpdateSolicitud`
- `date-fns`: `differenceInDays`, `formatDistanceToNow`, `parseISO`
- `./ModalCrearSolicitud`: modal de edición
- `./modal/ModalComentario/ModalComentariosSolicitud`: modal de comentarios
- `@/components/ui/*`: badge, button, card, dialog, separator, tooltip, avatar
