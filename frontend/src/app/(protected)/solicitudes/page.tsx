/**
 * Bandeja de Solicitudes — operativa principal de Mesa de Partes.
 * Ruta: /solicitudes
 *
 * Filtros sincronizados con la URL: page, page_size, estado, prioridad, busqueda, vista.
 * Los parámetros persisten al recargar o compartir la URL.
 *
 * "Filtros" abre un modal para estado y prioridad.
 * La búsqueda (busqueda) se sincroniza directamente desde el input con debounce.
 *
 * Vista-tabs (vista param): Todas | Mis áreas | Asignadas a mí | Creadas por mí
 * Cada pestaña es mutuamente excluyente respecto a la propiedad de la solicitud.
 */
"use client";

import { FileText, Filter, Plus, Search, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo, useState } from "react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageWrapper } from "@/components-app/page";
import type { FiltrosSolicitudesValues } from "@/features/tramites/components/FiltrosSolicitudesModal";
import { FiltrosSolicitudesModal } from "@/features/tramites/components/FiltrosSolicitudesModal";
import { SolicitudFormModal } from "@/features/tramites/components/forms/SolicitudFormModal";
import {
  SolicitudCard,
  SolicitudCardSkeleton,
} from "@/features/tramites/components/SolicitudCard";
import { useSolicitudes } from "@/features/tramites/hooks/useTramites";
import { useDebounce } from "@/hooks";
import { useUrlPagination } from "@/hooks/system/useUrlPagination";
import {
  ESTADO_SOLICITUD,
  type EstadoSolicitud,
  PRIORIDAD_SOLICITUD,
  type PrioridadSolicitud,
} from "@/shared/constants/tramite.tokens";

/** Vista-tabs posibles para la bandeja de solicitudes */
type VistaTab = "todas" | "mias_areas" | "asignadas" | "creadas";

const VISTA_TABS: { value: VistaTab; label: string }[] = [
  { value: "todas", label: "Todas" },
  { value: "mias_areas", label: "Mis áreas" },
  { value: "asignadas", label: "Asignadas a mí" },
  { value: "creadas", label: "Creadas por mí" },
];

export default function SolicitudesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // ── URL-synced pagination ────────────────────────────────────────────────────
  const { page, pageSize, onPageChange, onPageSizeChange, resetPageAndPush } =
    useUrlPagination();

  // ── Vista tab (top-level bandeja selector) ─────────────────────────────────
  const vista = (searchParams.get("vista") as VistaTab) || "todas";

  // ── Local search input (debounced before pushing to URL) ─────────────────────
  const [searchInput, setSearchInput] = useState(
    searchParams.get("busqueda") ?? "",
  );
  const debouncedSearch = useDebounce(searchInput, 300);

  // ── Filter state derived from URL ───────────────────────────────────────────
  const filtros = useMemo<{
    estado: EstadoSolicitud | "";
    prioridad: PrioridadSolicitud | "";
    busqueda: string;
    mis_areas: boolean;
    me: boolean;
    creadas_por_mi: boolean;
  }>(
    () => ({
      estado: (searchParams.get("estado") as EstadoSolicitud) || "",
      prioridad: (searchParams.get("prioridad") as PrioridadSolicitud) || "",
      busqueda: debouncedSearch,
      // Vista-derived ownership filters (mutually exclusive)
      mis_areas: vista === "mias_areas",
      me: vista === "asignadas",
      creadas_por_mi: vista === "creadas",
    }),
    [searchParams, debouncedSearch, vista],
  );

  // Sync search input changes to URL (no page reset)
  const handleSearchChange = useCallback(
    (value: string) => {
      setSearchInput(value);
      const params = new URLSearchParams(searchParams.toString());
      if (value.trim()) {
        params.set("busqueda", value.trim());
      } else {
        params.delete("busqueda");
      }
      // Do NOT reset page on search
      router.replace(`?${params.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  // ── Tab change handler ─────────────────────────────────────────────────────
  const handleVistaChange = useCallback(
    (newVista: VistaTab) => {
      resetPageAndPush({
        vista: newVista,
        // Clear ownership URL params — vista is the source of truth for ownership
        // Keep estado, prioridad, busqueda; clear solo_principal to avoid stale filter
        mis_areas: null,
        me: null,
        creadas_por_mi: null,
        solo_principal: null,
      });
    },
    [resetPageAndPush],
  );

  // ── Modal state ─────────────────────────────────────────────────────────────
  const [showFiltros, setShowFiltros] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  // ── Filter application from modal ───────────────────────────────────────────
  // When modal is open, mis_areas is driven by the vista tab (not the modal).
  // The modal should NOT set mis_areas since vista tabs control ownership.
  const applyFiltros = useCallback(
    (values: FiltrosSolicitudesValues) => {
      resetPageAndPush({
        estado: values.estado || null,
        prioridad: values.prioridad || null,
        solo_principal: null,
        // Do NOT pass mis_areas from modal — vista tabs own that concern
      });
    },
    [resetPageAndPush],
  );

  const clearFiltros = useCallback(() => {
    // Clear only modal-owned filters; vista tab ownership persists
    resetPageAndPush({ estado: null, prioridad: null, solo_principal: null });
  }, [resetPageAndPush]);

  // ── Clear all filters including search ──────────────────────────────────────
  const clearAllFilters = useCallback(() => {
    setSearchInput("");
    resetPageAndPush({
      estado: null,
      prioridad: null,
      busqueda: null,
      solo_principal: null,
      vista: "todas",
    });
  }, [resetPageAndPush]);

  // ── Active filter detection (for badges and clear button) ───────────────────
  //mis_areas and me/creadas_por_mi are shown as tab badges, not filter badges
  const hasActiveFilters = Boolean(
    debouncedSearch || filtros.estado || filtros.prioridad,
  );

  // ── API query ────────────────────────────────────────────────────────────────
  const pagination = useMemo(
    () => ({
      page,
      pageSize,
      page_size: pageSize,
      onPageChange,
      onPageSizeChange,
    }),
    [page, pageSize, onPageChange, onPageSizeChange],
  );

  const { items, total, totalPages, isLoading, isError, refetch } =
    useSolicitudes(filtros, pagination);

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <>
      <PageWrapper
        title="Bandeja de Solicitudes"
        description="Listado operativo de solicitudes registradas"
        icon={<FileText className="h-6 w-6 text-primary" />}
      >
        {/* Vista tabs */}
        <Tabs value={vista} onValueChange={(v) => handleVistaChange(v as VistaTab)}>
          <TabsList className="mb-4">
            {VISTA_TABS.map((tab) => (
              <TabsTrigger key={tab.value} value={tab.value}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        {/* Filter row */}
        <div className="app-toolbar-card space-y-3">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
            {/* Search input */}
            <div className="relative min-w-0 flex-1">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por ID, documento, persona o asunto..."
                value={searchInput}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="h-11 rounded-xl pl-10 pr-10"
              />
              {searchInput && (
                <button
                  type="button"
                  onClick={() => handleSearchChange("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label="Limpiar búsqueda"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            <div className="flex flex-wrap items-center justify-end gap-3">
              {/* Filter modal trigger */}
              <Button
                variant={hasActiveFilters ? "default" : "outline"}
                className="gap-2 h-10 rounded-xl"
                onClick={() => setShowFiltros(true)}
              >
                <Filter className="h-4 w-4" />
                Filtros
                {hasActiveFilters && (
                  <span className="ml-1 flex h-4 w-4 items-center justify-center rounded-full bg-white/20 text-xs font-bold">
                    {[filtros.estado, filtros.prioridad].filter(Boolean)
                      .length + (debouncedSearch ? 1 : 0)}
                  </span>
                )}
              </Button>

              <Button
                className="gap-2 h-10 rounded-xl font-bold btn-wine-gradient-hover shrink-0"
                onClick={() => setShowCreate(true)}
              >
                <Plus className="h-4 w-4" />
                Nueva Solicitud
              </Button>

              {/* Clear all filters */}
              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearAllFilters}
                  className="h-9 text-destructive hover:text-destructive"
                >
                  Limpiar filtros
                </Button>
              )}
            </div>
          </div>

          {/* Active filter badges */}
          {hasActiveFilters && (
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span>Filtros activos:</span>
              {debouncedSearch && (
                <span className="bg-primary/10 border border-primary/20 px-2 py-0.5 rounded-full">
                  Búsqueda: {debouncedSearch}
                </span>
              )}
              {filtros.estado && (
                <span className="bg-primary/10 border border-primary/20 px-2 py-0.5 rounded-full">
                  Estado: {ESTADO_SOLICITUD[filtros.estado].label}
                </span>
              )}
              {filtros.prioridad && (
                <span className="bg-primary/10 border border-primary/20 px-2 py-0.5 rounded-full">
                  Prioridad: {PRIORIDAD_SOLICITUD[filtros.prioridad].label}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Card grid */}
        <div>
          {/* Error state */}
          {isError && (
            <div className="app-card flex min-h-[22rem] flex-col items-center justify-center gap-4 p-10 text-center">
              <FileText className="h-10 w-10 text-destructive" />
              <div>
                <p className="text-sm font-medium text-destructive">
                  Error al cargar solicitudes
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  No se pudieron obtener los datos. Intente nuevamente.
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                Reintentar
              </Button>
            </div>
          )}

          {/* Loading skeleton */}
          {!isError && isLoading && (
            <div className="app-results-grid">
              {Array.from({ length: pageSize || 6 }).map((_, i) => (
                <SolicitudCardSkeleton key={i} />
              ))}
            </div>
          )}

          {/* Empty state */}
          {!isError && !isLoading && items.length === 0 && (
            <div className="app-card flex min-h-[22rem] flex-col items-center justify-center gap-3 p-10 text-center">
              <FileText className="h-10 w-10 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium text-foreground">
                  {hasActiveFilters
                    ? "No hay solicitudes que coincidan con los filtros"
                    : "No hay solicitudes registradas"}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {hasActiveFilters
                    ? "Probá cambiando o limpiando los filtros."
                    : "Las solicitudes que crees aparecerán en esta bandeja."}
                </p>
              </div>
              {hasActiveFilters && (
                <Button variant="outline" size="sm" onClick={clearAllFilters}>
                  Limpiar filtros
                </Button>
              )}
            </div>
          )}

          {/* Card grid */}
          {!isError && !isLoading && items.length > 0 && (
            <div className="app-results-grid">
              {items.map((item) => (
                <SolicitudCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && !isError && (
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            totalItems={total}
            pageSize={pageSize}
            onPageChange={onPageChange}
            onPageSizeChange={onPageSizeChange}
          />
        )}
      </PageWrapper>

      {/* Filtros modal — does NOT include mis_areas since tabs own ownership */}
      <FiltrosSolicitudesModal
        open={showFiltros}
        onOpenChange={setShowFiltros}
        currentValues={{
          estado: filtros.estado,
          prioridad: filtros.prioridad,
          // mis_areas always false — tabs own that filter
          mis_areas: false,
        }}
        onAplicar={applyFiltros}
        onLimpiar={clearFiltros}
        hasActiveFilters={hasActiveFilters}
      />

      {/* Modal de creación de solicitud */}
      <SolicitudFormModal
        open={showCreate}
        onOpenChange={setShowCreate}
        onSuccess={() => setShowCreate(false)}
      />
    </>
  );
}
