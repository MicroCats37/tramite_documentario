"use client";

import { Bell } from "lucide-react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
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
 * Topbar component — sits above the main content area in the protected layout.
 * Contains only the notifications dropdown (right-aligned).
 */
export function Topbar() {
  const router = useRouter();
  const { items, total } = useNotificaciones(1);
  const { data: summary } = useNotificacionSummary();

  // Unread count: prefer summary.sin_leer when available, else derive from list.
  const unreadCount =
    summary?.sin_leer ??
    items.filter((n) => n.estado_individual === "NO_VISTA").length;

  return (
    <header className="pointer-events-none absolute right-6 top-5 z-20 flex h-10 items-center justify-end lg:right-8">
      {/* Right: notifications dropdown */}
      <div className="pointer-events-auto flex items-center gap-2">
        <DropdownMenu>
          <Tooltip>
            <TooltipTrigger asChild>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="relative h-10 w-10 rounded-xl border border-primary/10 bg-background/85 text-muted-foreground shadow-sm backdrop-blur transition-all hover:bg-primary/10 hover:text-primary hover:shadow-md"
                >
                  <Bell className="h-4 w-4" />
                  {/* Unread indicator */}
                  {unreadCount > 0 && (
                    <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground">
                      {unreadCount > 9 ? "9+" : unreadCount}
                    </span>
                  )}
                </Button>
              </DropdownMenuTrigger>
            </TooltipTrigger>
            <TooltipContent>
              <p>Notificaciones</p>
            </TooltipContent>
          </Tooltip>

          <DropdownMenuContent align="end" className="w-80">
            {/* Header */}
            <div className="flex items-center justify-between px-2 py-1.5">
              <span className="text-sm font-semibold">Notificaciones</span>
              {/* Total: prefer summary.total when available, else use list-derived total. */}
              {(summary?.total ?? total) > 0 && (
                <span className="text-xs text-muted-foreground">
                  {summary?.total ?? total} total
                </span>
              )}
            </div>
            <DropdownMenuSeparator />

            {/* Notification list */}
            {items.length === 0 ? (
              <div className="py-6 text-center text-sm text-muted-foreground">
                Sin notificaciones
              </div>
            ) : (
              items.slice(0, 5).map((notificacion) => {
                const isUnread = notificacion.estado_individual === "NO_VISTA";
                return (
                  <DropdownMenuItem
                    key={notificacion.id}
                    className="flex flex-col items-start gap-1.5 px-2 py-2.5 cursor-pointer"
                    onClick={() =>
                      router.push(`/notificaciones/${notificacion.id}`)
                    }
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
                    <div className="flex w-full items-center gap-2">
                      {notificacion.ambito && (
                        <Badge
                          variant="secondary"
                          className="text-[10px] px-1.5 py-0"
                        >
                          {notificacion.ambito}
                        </Badge>
                      )}
                      <span className="text-xs text-muted-foreground">
                        {formatDate(notificacion.ocurrido_en)}
                      </span>
                    </div>
                  </DropdownMenuItem>
                );
              })
            )}

            {/* Footer */}
            {total > 0 && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="cursor-pointer justify-center text-center text-sm font-medium text-primary hover:bg-primary/5"
                  onClick={() => router.push("/notificaciones")}
                >
                  Ver todas las notificaciones
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
