"use client";

import { BellOff } from "lucide-react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useNotificaciones,
  useNotificacionSummary,
} from "@/features/notificaciones/hooks";
import { cn } from "@/lib/utils";

/**
 * Formats a date string to a short local date string.
 */
function formatDate(fechaEvento: string): string {
  try {
    const date = new Date(fechaEvento);
    return date.toLocaleDateString("es-PE", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return fechaEvento;
  }
}

/**
 * Truncates message text to a maximum length for preview display.
 */
function truncateMessage(
  mensaje: string | null | undefined,
  maxLength = 60,
): string {
  if (!mensaje) return "";
  if (mensaje.length <= maxLength) return mensaje;
  return `${mensaje.slice(0, maxLength).trimEnd()}…`;
}

interface NotificationsPanelProps {
  /** Called when the dropdown should close (optional). */
  onClose?: () => void;
}

/**
 * NotificationsPanel — renders inside a DropdownMenuContent.
 * Displays the notification list fetched via useNotificaciones(1) with loading,
 * empty, and populated states.
 *
 * Auto-refreshes when a WebSocket `notification.created` event fires because
 * useNotificationRealtime invalidates the `["notificaciones","list"]` and
 * `["notificaciones","summary"]` query keys, which triggers a background refetch
 * of the data used by this component.
 */
export function NotificationsPanel({ onClose }: NotificationsPanelProps) {
  const router = useRouter();
  const { items, total, isLoading } = useNotificaciones(1);
  const { data: summary } = useNotificacionSummary();

  const handleItemClick = (id: string) => {
    onClose?.();
    router.push(`/notificaciones/${id}`);
  };

  const handleViewAll = () => {
    onClose?.();
    router.push("/notificaciones");
  };

  // Loading skeleton — shown while initial fetch is in flight and list is empty.
  if (isLoading && items.length === 0) {
    return (
      <>
        <div className="flex items-center justify-between px-2 py-1.5">
          <span className="text-sm font-semibold">Notificaciones</span>
        </div>
        <DropdownMenuSeparator />
        <div className="flex flex-col gap-2 p-2">
          <div className="flex flex-col gap-1.5">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          <div className="flex flex-col gap-1.5">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          <div className="flex flex-col gap-1.5">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      </>
    );
  }

  // Empty state.
  if (items.length === 0) {
    return (
      <>
        <div className="flex items-center justify-between px-2 py-1.5">
          <span className="text-sm font-semibold">Notificaciones</span>
          {total > 0 && (
            <span className="text-xs text-muted-foreground">{total} total</span>
          )}
        </div>
        <DropdownMenuSeparator />
        <div className="flex flex-col items-center justify-center py-8 gap-3 text-center">
          <div className="p-3 bg-muted rounded-full">
            <BellOff className="h-6 w-6 text-muted-foreground" />
          </div>
          <div>
            <p className="text-sm font-medium">Sin notificaciones</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              No tienes notificaciones pendientes
            </p>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between px-2 py-1.5">
        <span className="text-sm font-semibold">Notificaciones</span>
        {(summary?.total ?? total) > 0 && (
          <span className="text-xs text-muted-foreground">
            {summary?.total ?? total} total
          </span>
        )}
      </div>
      <DropdownMenuSeparator />

      {/* Notification list */}
      {items.slice(0, 5).map((notificacion) => {
        const isUnread = notificacion.estado_individual === "NO_VISTA";
        return (
          <DropdownMenuItem
            key={notificacion.id}
            className="flex flex-col items-start gap-1.5 px-2 py-2.5 cursor-pointer"
            onSelect={() => handleItemClick(notificacion.id)}
          >
            <div className="flex w-full items-start justify-between gap-2">
              <span
                className={cn(
                  "text-sm",
                  isUnread ? "font-semibold" : "font-normal",
                )}
              >
                {notificacion.titulo}
              </span>
              {isUnread && (
                <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-destructive" />
              )}
            </div>

            {/* Message preview */}
            {notificacion.mensaje && (
              <p className="text-xs text-muted-foreground line-clamp-2">
                {truncateMessage(notificacion.mensaje)}
              </p>
            )}

            {/* Event badge + date */}
            <div className="flex w-full items-center gap-2">
              {notificacion.evento && (
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                  {notificacion.evento}
                </Badge>
              )}
              <span className="text-xs text-muted-foreground">
                {formatDate(notificacion.ocurrido_en)}
              </span>
            </div>
          </DropdownMenuItem>
        );
      })}

      {/* Footer */}
      {total > 0 && (
        <>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="cursor-pointer justify-center text-center text-sm font-medium text-primary hover:bg-primary/5"
            onSelect={handleViewAll}
          >
            Ver todas las notificaciones
          </DropdownMenuItem>
        </>
      )}
    </>
  );
}
