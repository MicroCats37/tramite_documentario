/**
 * Centro de Notificaciones — bandeja individualizada del usuario.
 * Ruta: /notificaciones
 *
 * Muestra listado paginado de notificaciones con badges de estado.
 * Usa useNotificaciones(), useMarkVista() y useDescartarNotificacion().
 */
"use client";

import { Bell, BellOff, CheckCheck, ExternalLink } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ESTADO_NOTIFICACION,
  type EstadoNotificacionIndividual,
} from "@/shared/constants/tramite.tokens";
import {
  useNotificaciones,
  useMarkVista,
  useDescartarNotificacion,
} from "@/features/notificaciones/hooks/useNotificaciones";
import type { NotificationItem } from "@/features/notificaciones/schemas/notificacion.schema";
import { toast } from "sonner";
import { PageWrapper } from "@/components-app/page";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("es-PE", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

// ── Skeleton ───────────────────────────────────────────────────────────────────

function ListSkeleton() {
  return (
    <div className="app-page">
      <div className="app-page-header ">
        <Skeleton className="h-10 w-64" />
      </div>
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-32 w-full" />
        ))}
      </div>
    </div>
  );
}

// ── Empty State ───────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <PageWrapper
      title="Centro de Notificaciones"
      description="Avisos y eventos de tus solicitudes"
      icon={<Bell className="h-6 w-6 text-primary" />}
    >
      <div className="app-card flex flex-col items-center justify-center py-16 gap-4 text-center">
        <div className="p-4 bg-muted rounded-full">
          <BellOff className="h-8 w-8 text-muted-foreground" />
        </div>
        <div>
          <h3 className="font-semibold text-lg">Sin notificaciones</h3>
          <p className="text-sm text-muted-foreground mt-1">
            No tienes notificaciones pendientes
          </p>
        </div>
      </div>
    </PageWrapper>
  );
}

// ── Notification Card ─────────────────────────────────────────────────────────

interface NotificationCardProps {
  item: NotificationItem;
  onMarcarVista: (id: string) => void;
  onDescartar: (id: string) => void;
  onNavigate: (item: NotificationItem) => void;
  isMarkingVista: boolean;
  isDiscarding: boolean;
}

function NotificationCard({
  item,
  onMarcarVista,
  onDescartar,
  onNavigate,
  isMarkingVista,
  isDiscarding,
}: NotificationCardProps) {
  const estadoToken =
    ESTADO_NOTIFICACION[item.estado_individual as EstadoNotificacionIndividual];

  const canMarkVista =
    item.estado_individual === "NO_VISTA" || item.estado_individual === "VISTA";
  const canDiscard = item.estado_individual !== "DESCARTADA";

  return (
    <div className="app-card p-4 space-y-3">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-medium text-sm truncate">{item.titulo}</h3>
            <Badge className={estadoToken.badgeClass}>{estadoToken.label}</Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {item.tipo_evento}
          </p>
        </div>
        <span className="text-xs text-muted-foreground shrink-0">
          {formatDate(item.fecha_evento)}
        </span>
      </div>

      {/* Context info */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span className="bg-muted px-2 py-0.5 rounded-md">{item.area_nombre}</span>
        {item.solicitud_id_publico && (
          <span className="font-mono">{item.solicitud_id_publico}</span>
        )}
        {item.periodo_ciclo != null && (
          <span>Ciclo {item.periodo_ciclo}</span>
        )}
        {item.periodo_activo ? (
          <span className="success-text">Período activo</span>
        ) : (
          <span className="text-muted-foreground">Período cerrado</span>
        )}
        {item.participo ? (
          <span className="text-primary font-medium">Participas</span>
        ) : (
          <span className="text-muted-foreground">No participas</span>
        )}
      </div>

      {/* Resumen de solicitud */}
      {item.solicitud_asunto && (
        <p className="text-xs text-muted-foreground line-clamp-2">
          {item.solicitud_asunto}
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1 border-t">
        {canMarkVista && (
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 h-8 text-xs"
            onClick={() => onMarcarVista(item.id)}
            disabled={isMarkingVista || isDiscarding}
          >
            <CheckCheck className="h-3.5 w-3.5" />
            Marcar vista
          </Button>
        )}
        {canDiscard && (
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 h-8 text-xs text-muted-foreground hover:text-foreground"
            onClick={() => onDescartar(item.id)}
            disabled={isMarkingVista || isDiscarding}
          >
            <BellOff className="h-3.5 w-3.5" />
            Descartar
          </Button>
        )}
        {item.solicitud_id_publico && (
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 h-8 text-xs ml-auto"
            onClick={() => onNavigate(item)}
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Abrir solicitud
          </Button>
        )}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function NotificacionesPage() {
  const router = useRouter();

  const {
    items,
    total,
    page,
    pageSize,
    totalPages,
    isLoading,
    isError,
    onPageChange,
    refetch,
  } = useNotificaciones();

  const { mutateAsync: markVista, isPending: isMarkingVista } = useMarkVista();
  const { mutateAsync: discard, isPending: isDiscarding } = useDescartarNotificacion();

  const handleMarcarVista = async (id: string) => {
    try {
      await markVista(id);
      toast.success("Notificación marcada como vista");
    } catch {
      toast.error("No se pudo marcar la notificación como vista");
    }
  };

  const handleDescartar = async (id: string) => {
    try {
      await discard(id);
      toast.success("Notificación descartada");
    } catch {
      toast.error("No se pudo descartar la notificación");
    }
  };

  const handleNavigate = (item: NotificationItem) => {
    if (item.solicitud_id_publico) {
      // Navigate to the related solicitud — the id is the solicitud uuid, not id_publico
      // We need to use the solicitud_id if available for navigation
      router.push(`/notificaciones/${item.id}`);
    }
  };

  if (isLoading) return <ListSkeleton />;

  if (isError) {
    return (
      <PageWrapper
        title="Centro de Notificaciones"
        description="Avisos y eventos de tus solicitudes"
        icon={<Bell className="h-6 w-6 text-primary" />}
      >
        <div className="app-card flex flex-col items-center justify-center py-16 gap-4 text-center">
          <div className="p-4 bg-destructive/10 rounded-full">
            <Bell className="h-8 w-8 text-destructive" />
          </div>
          <div>
            <h3 className="font-semibold text-lg">Error al cargar</h3>
            <p className="text-sm text-muted-foreground mt-1">
              No se pudieron obtener las notificaciones
            </p>
          </div>
          <Button variant="outline" onClick={() => refetch()}>
            Reintentar
          </Button>
        </div>
      </PageWrapper>
    );
  }

  if (!isLoading && items.length === 0) return <EmptyState />;

  return (
    <PageWrapper
      title="Centro de Notificaciones"
      description={
        total > 0
          ? `${total} notificación${total !== 1 ? "es" : ""} — página ${page} de ${totalPages}`
          : "Avisos y eventos de tus solicitudes"
      }
      icon={<Bell className="h-6 w-6 text-primary" />}
    >

      {/* Notification list */}
      <div className="space-y-4">
        {items.map((item) => (
          <NotificationCard
            key={item.id}
            item={item}
            onMarcarVista={handleMarcarVista}
            onDescartar={handleDescartar}
            onNavigate={handleNavigate}
            isMarkingVista={isMarkingVista}
            isDiscarding={isDiscarding}
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center mt-6">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
            >
              Anterior
            </Button>
            <span className="text-sm text-muted-foreground">
              Página {page} de {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
            >
              Siguiente
            </Button>
          </div>
        </div>
      )}
    </PageWrapper>
  );
}
