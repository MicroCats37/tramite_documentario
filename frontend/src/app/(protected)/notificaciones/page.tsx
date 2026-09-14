/**
 * Centro de Notificaciones — bandeja individualizada del usuario.
 * Ruta: /notificaciones
 *
 * MVP profesional: tabs de filtro, summary cards, paginación.
 * Usa useNotificacionSummary(), useNotificaciones(), useMarkVista(),
 * useDescartarNotificacion() y componentes Task 4.
 */
"use client";

import { Bell } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { PageWrapper } from "@/components-app/page";
import {
  NotificationCard,
  NotificationEmptyState,
  type NotificationFilterTab,
  NotificationSummaryCards,
  NotificationTabs,
} from "@/features/notificaciones/components";
import {
  useMarkVista,
  useNotificaciones,
  useNotificacionSummary,
} from "@/features/notificaciones/hooks/useNotificaciones";
import type { NotificationListItem } from "@/features/notificaciones/schemas/notificacion.schema";

// ── Constants ─────────────────────────────────────────────────────────────────

const PAGE_SIZE_OPTIONS = [5, 10, 20];

// ── Skeleton ─────────────────────────────────────────────────────────────────

function ListSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="app-card p-4 space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 space-y-2">
              <div className="h-4 w-48 rounded-md bg-muted animate-pulse" />
              <div className="h-3 w-32 rounded-md bg-muted animate-pulse" />
            </div>
            <div className="h-3 w-20 rounded-md bg-muted animate-pulse" />
          </div>
          <div className="flex gap-4">
            <div className="h-3 w-24 rounded-md bg-muted animate-pulse" />
            <div className="h-3 w-20 rounded-md bg-muted animate-pulse" />
          </div>
          <div className="flex gap-2 pt-1 border-t">
            <div className="h-7 w-28 rounded-md bg-muted animate-pulse" />
            <div className="h-7 w-24 rounded-md bg-muted animate-pulse" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function NotificacionesPage() {
  const router = useRouter();

  // ── Tab filter state ──────────────────────────────────────────────────────
  // PENDIENTE maps to VISTA backend state (notifications that have been viewed
  // but not yet acted upon — considered "pending" from the user's perspective).
  const [activeTab, setActiveTab] = useState<NotificationFilterTab>("TODAS");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE_OPTIONS[0]);

  // ── Data hooks ────────────────────────────────────────────────────────────
  const { data: summary, isLoading: isSummaryLoading } =
    useNotificacionSummary();

  const { items, total, isLoading, isError, refetch } = useNotificaciones({
    estado: undefined,
    initialPage: 1,
    pageSize,
  });

  const { mutateAsync: markVista, isPending: isMarkingVista } = useMarkVista();

  // ── Client-side filter ────────────────────────────────────────────────────
  // Backend returns all items; filter by tab client-side.
  // PENDIENTE tab → VISTA backend state (viewed but pending user action).
  const filteredItems = (() => {
    if (activeTab === "TODAS") return items;
    if (activeTab === "PENDIENTE") {
      return items.filter((item) => item.estado_individual === "VISTA");
    }
    return items.filter((item) => item.estado_individual === activeTab);
  })();

  // ── Client-side pagination over filtered items ──────────────────────────────
  const totalFiltered = filteredItems.length;
  const totalPages = Math.max(1, Math.ceil(totalFiltered / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const paginatedItems = filteredItems.slice(
    (safePage - 1) * pageSize,
    safePage * pageSize,
  );

  // Reset to page 1 when tab changes.
  const handleTabChange = (tab: NotificationFilterTab) => {
    setActiveTab(tab);
    setCurrentPage(1);
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handlePageSizeChange = (size: number) => {
    setPageSize(size);
    setCurrentPage(1);
  };

  // ── Actions ───────────────────────────────────────────────────────────────
  const handleMarcarVista = async (id: string) => {
    try {
      await markVista(id);
      toast.success("Notificación marcada como vista");
    } catch {
      toast.error("No se pudo marcar la notificación como vista");
    }
  };

  const handleNavigate = (item: NotificationListItem) => {
    // Always navigate to notification detail; vista/abrir are handled there.
    router.push(`/notificaciones/${item.id}`);
  };

  // ── Loading ───────────────────────────────────────────────────────────────
  if (isLoading || isSummaryLoading) {
    return (
      <PageWrapper
        title="Centro de Notificaciones"
        description="Cargando notificaciones…"
        icon={<Bell className="h-6 w-6 text-primary" />}
      >
        <ListSkeleton />
      </PageWrapper>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────
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

  // ── Empty state (no notifications at all) ─────────────────────────────────
  if (total === 0) {
    return (
      <PageWrapper
        title="Centro de Notificaciones"
        description="Avisos y eventos de tus solicitudes"
        icon={<Bell className="h-6 w-6 text-primary" />}
      >
        <NotificationEmptyState activeFilter="TODAS" />
      </PageWrapper>
    );
  }

  // ── Description ────────────────────────────────────────────────────────────
  const description =
    totalFiltered > 0
      ? `${totalFiltered} notificación${totalFiltered !== 1 ? "es" : ""}${
          activeTab !== "TODAS" ? ` — página ${safePage} de ${totalPages}` : ""
        }`
      : "Avisos y eventos de tus solicitudes";

  return (
    <PageWrapper
      title="Centro de Notificaciones"
      description={description}
      icon={<Bell className="h-6 w-6 text-primary" />}
    >
      {/* Summary strip */}
      <NotificationSummaryCards
        summary={summary ?? undefined}
        isLoading={isSummaryLoading}
      />

      {/* Filter tabs */}
      <NotificationTabs value={activeTab} onChange={handleTabChange} />

      {/* Notification list */}
      {paginatedItems.length === 0 ? (
        <NotificationEmptyState activeFilter={activeTab} />
      ) : (
        <div className="space-y-4">
          {paginatedItems.map((item) => (
            <NotificationCard
              key={item.id}
              item={item}
              onMarcarVista={handleMarcarVista}
              onNavigate={handleNavigate}
              isMarkingVista={isMarkingVista}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalFiltered > 0 && totalPages > 1 && (
        <Pagination
          currentPage={safePage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
          onPageSizeChange={handlePageSizeChange}
          totalItems={totalFiltered}
          pageSize={pageSize}
        />
      )}
    </PageWrapper>
  );
}
