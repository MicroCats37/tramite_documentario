/**
 * Bandeja de Solicitudes — operativa principal de Mesa de Partes.
 * Ruta: /solicitudes
 *
 * Muestra listado paginado con filtros por búsqueda, estado y prioridad.
 * Grid de SolicitudCard con paginación legacy. Botón "Nueva Solicitud"
 * abre el SolicitudFormModal (AppFormModal + GenericForm con un solo
 * formulario de secciones claras — sin wizard/stepper).
 */
"use client";

import { FileText, Plus, Search } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Pagination } from "@/components/genericPagination/Pagination";
import { PageWrapper } from "@/components-app/page";
import {
  ESTADO_SOLICITUD,
  PRIORIDAD_SOLICITUD,
  type EstadoSolicitud,
  type PrioridadSolicitud,
} from "@/shared/constants/tramite.tokens";
import {
  SolicitudCard,
  SolicitudCardSkeleton,
} from "@/features/tramites/components/SolicitudCard";
import { SolicitudFormModal } from "@/features/tramites/components/forms/SolicitudFormModal";
import { useSolicitudes } from "@/features/tramites/hooks/useTramites";
import { useDebounce } from "@/hooks";

export default function SolicitudesPage() {
  const [search, setSearch] = useState("");
  const [estado, setEstado] = useState<EstadoSolicitud | "">("");
  const [prioridad, setPrioridad] = useState<PrioridadSolicitud | "">("");
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
  } = useSolicitudes();

  const hasActiveFilters = debouncedSearch || estado || prioridad;

  return (
    <>
      <PageWrapper
        title="Bandeja de Solicitudes"
        description="Listado operativo de solicitudes registradas"
        icon={<FileText className="h-6 w-6 text-primary" />}
      >
        {/* Filter row */}
        <div className="app-toolbar-card space-y-3">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
            {/* Search input with debounce */}
            <div className="relative min-w-0 flex-1">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por ID, documento, persona o asunto..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="h-11 rounded-xl pl-10"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-3">

            {/* Estado select */}
            <Select
              value={estado}
              onValueChange={(val) => {
                setEstado(val as EstadoSolicitud | "");
                onPageChange(1);
              }}
            >
              <SelectTrigger className="h-10 w-[160px] rounded-xl">
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">Todos los estados</SelectItem>
                <SelectItem value="REGISTRADA">Registrada</SelectItem>
                <SelectItem value="EN_GESTION">En Gestión</SelectItem>
                <SelectItem value="FINALIZADA">Finalizada</SelectItem>
                <SelectItem value="ANULADA">Anulada</SelectItem>
              </SelectContent>
            </Select>

            {/* Prioridad select */}
            <Select
              value={prioridad}
              onValueChange={(val) => {
                setPrioridad(val as PrioridadSolicitud | "");
                onPageChange(1);
              }}
            >
              <SelectTrigger className="h-10 w-[160px] rounded-xl">
                <SelectValue placeholder="Prioridad" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">Todas las prioridades</SelectItem>
                <SelectItem value="BAJA">Baja</SelectItem>
                <SelectItem value="MEDIA">Media</SelectItem>
                <SelectItem value="ALTA">Alta</SelectItem>
                <SelectItem value="URGENTE">Urgente</SelectItem>
              </SelectContent>
            </Select>

            <Button
              className="gap-2 h-10 rounded-xl font-bold btn-wine-gradient-hover shrink-0"
              onClick={() => setShowCreate(true)}
            >
              <Plus className="h-4 w-4" />
              Nueva Solicitud
            </Button>

            {/* Clear filters */}
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSearch("");
                  setEstado("");
                  setPrioridad("");
                  onPageChange(1);
                }}
                className="h-9 text-destructive hover:text-destructive"
              >
                Limpiar filtros
              </Button>
            )}
          </div>

          {/* Active filter count */}
          {hasActiveFilters && (
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span>Filtros activos:</span>
              {debouncedSearch && (
                <span className="bg-primary/10 border border-primary/20 px-2 py-0.5 rounded-full">
                  Búsqueda: {debouncedSearch}
                </span>
              )}
              {estado && (
                <span className="bg-primary/10 border border-primary/20 px-2 py-0.5 rounded-full">
                  Estado: {ESTADO_SOLICITUD[estado as EstadoSolicitud].label}
                </span>
              )}
              {prioridad && (
                <span className="bg-primary/10 border border-primary/20 px-2 py-0.5 rounded-full">
                  Prioridad: {PRIORIDAD_SOLICITUD[prioridad as PrioridadSolicitud].label}
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
                  No hay solicitudes registradas
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Las solicitudes que crees aparecerán en esta bandeja.
                </p>
              </div>
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

      {/* Modal de creación de solicitud (formulario de una sola vista) */}
      <SolicitudFormModal
        open={showCreate}
        onOpenChange={setShowCreate}
        onSuccess={() => setShowCreate(false)}
      />
    </>
  );
}
