"use client";

import { Bell } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { NotificationsPanel } from "@/features/notificaciones/components/NotificationsPanel";
import {
  useNotificacionSummary,
  useNotificationWebSocket,
} from "@/features/notificaciones/hooks";

/**
 * Topbar component — sits above the main content area in the protected layout.
 * Contains only the notifications dropdown (right-aligned).
 */
export function Topbar() {
  const [open, setOpen] = useState(false);
  const { data: summary } = useNotificacionSummary();
  const { state: wsState } = useNotificationWebSocket();

  const unreadCount = summary?.sin_leer ?? 0;

  return (
    <header className="pointer-events-none absolute right-6 top-5 z-20 flex h-10 items-center justify-end lg:right-8">
      {/* Right: notifications dropdown */}
      <div className="pointer-events-auto flex items-center gap-2">
        <DropdownMenu open={open} onOpenChange={setOpen}>
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
                  {/* WS debug indicator — only visible when NEXT_PUBLIC_WS_DEBUG=true */}
                  {process.env.NEXT_PUBLIC_WS_DEBUG === "true" && (
                    <span
                      className="absolute bottom-0.5 right-0.5 flex items-center justify-center rounded-full px-1 text-[8px] font-mono font-bold leading-none"
                      title={`WS: ${wsState}`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          wsState === "connected"
                            ? "bg-green-500"
                            : wsState === "connecting" ||
                                wsState === "reconnecting"
                              ? "bg-yellow-500"
                              : "bg-gray-400"
                        }`}
                      />
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
            <NotificationsPanel onClose={() => setOpen(false)} />
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
