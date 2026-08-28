/**
 * Bandeja de Expedientes — consulta documental.
 * Ruta: /expedientes
 *
 * Muestra listado paginado con búsqueda por ID público, documento,
 * persona o asunto. Los datos se cargan desde useExpedientes()
 * usando grid de ExpedienteCard.
 */
"use client";

import { FolderSearch, Search, Plus } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/genericPagination/Pagination";
import { PageWrapper } from "@/components-app/page";
import { ExpedienteCard, ExpedienteCardSkeleton } from "@/features/tramites/components/ExpedienteCard";
import { ExpedienteFormModal } from "@/features/tramites/components/forms/ExpedienteFormModal";
import { useExpedientes } from "@/features/tramites/hooks/useTramites";
import { useDebounce } from "@/hooks";

export default function ExpedientesPage() {
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const debouncedSearch = useDebounce(search, 300);

  const {
    items,
    total,
    page,
    pageSize,
    totalPages,
    isLoading,
    isError,
    onPageChange,
    onPageSizeChange,
    refetch,
  } = useExpedientes();

  return (
    <>
      <PageWrapper
        title="Consulta Documental"
        description="Expedientes registrados en el sistema"
        icon={<FolderSearch className="h-6 w-6 text-primary" />}
        actions={
          <Button
            className="gap-2 h-11 rounded-xl font-bold btn-wine-gradient-hover shrink-0"
            onClick={() => setShowCreate(true)}
          >
            <Plus className="h-4 w-4" />
            Nuevo Expediente
          </Button>
        }
      >
        {/* Filter row */}
        <div className="app-card p-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* Search input with debounce */}
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por ID público, documento, persona o asunto..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 h-9 rounded-lg"
              />
            </div>

            {/* Clear search */}
            {debouncedSearch && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSearch("");
                  onPageChange(1);
                }}
                className="h-9 text-destructive hover:text-destructive"
              >
                Limpiar búsqueda
              </Button>
            )}
          </div>

          {/* Active filter indicator */}
          {debouncedSearch && (
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span>Filtros activos:</span>
              <span className="bg-primary/10 border border-primary/20 px-2 py-0.5 rounded-full">
                Búsqueda: {debouncedSearch}
              </span>
            </div>
          )}
        </div>

        {/* Card grid */}
        <div className="mt-6">
          {/* Error state */}
          {isError && (
            <div className="flex flex-col items-center justify-center py-12 gap-4 text-center">
              <FolderSearch className="h-10 w-10 text-destructive" />
              <div>
                <p className="text-sm font-medium text-destructive">
                  Error al cargar expedientes
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
            <div className="grid grid-cols-1 gap-4">
              {Array.from({ length: pageSize || 6 }).map((_, i) => (
                <ExpedienteCardSkeleton key={i} />
              ))}
            </div>
          )}

          {/* Empty state */}
          {!isError && !isLoading && items.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
              <FolderSearch className="h-10 w-10 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium text-foreground">
                  No hay expedientes registrados
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Los expedientes creados aparecerán en esta consulta.
                </p>
              </div>
            </div>
          )}

          {/* Card grid */}
          {!isError && !isLoading && items.length > 0 && (
            <div className="grid grid-cols-1 gap-4">
              {items.map((item) => (
                <ExpedienteCard key={item.id} item={item} />
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

      {/* Modal de creación de expediente (GenericModal + GenericForm + Smart Fields) */}
      <ExpedienteFormModal
        open={showCreate}
        onOpenChange={setShowCreate}
        onSuccess={() => setShowCreate(false)}
      />
    </>
  );
}
