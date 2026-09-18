"use client";

/**
 * FiltrosSolicitudesModal — modal de filtros avanzados para la bandeja de solicitudes.
 *
 * Permite filtrar por estado y prioridad. Los valores se aplican al hacer clic en
 * "Aplicar filtros", lo que actualiza la URL y dispara la query con los nuevos filtros.
 *
 * Estado y prioridad vacío ("") significan "todos" — el backend filtra solo cuando
 * el valor no es vacío ni "ALL".
 */
import { Filter } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  EstadoSolicitud,
  PrioridadSolicitud,
} from "@/shared/constants/tramite.tokens";

export interface FiltrosSolicitudesValues {
  estado: EstadoSolicitud | "";
  prioridad: PrioridadSolicitud | "";
  mis_areas: boolean;
}

interface FiltrosSolicitudesModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Valores actuales de los filtros (ledos de la URL) */
  currentValues: FiltrosSolicitudesValues;
  /** Callback invocado al aplicar — recibe los nuevos valores de filtro */
  onAplicar: (values: FiltrosSolicitudesValues) => void;
  onLimpiar: () => void;
  hasActiveFilters: boolean;
}

export function FiltrosSolicitudesModal({
  open,
  onOpenChange,
  currentValues,
  onAplicar,
  onLimpiar,
  hasActiveFilters,
}: FiltrosSolicitudesModalProps) {
  const [localEstado, setLocalEstado] = useState<EstadoSolicitud | "">(
    currentValues.estado,
  );
  const [localPrioridad, setLocalPrioridad] = useState<PrioridadSolicitud | "">(
    currentValues.prioridad,
  );

  // Sincronizar estado local cuando el modal se abre con valores actualizados
  useEffect(() => {
    if (open) {
      setLocalEstado(currentValues.estado);
      setLocalPrioridad(currentValues.prioridad);
    }
  }, [open, currentValues.estado, currentValues.prioridad]);

  const handleClose = useCallback(
    (nextOpen: boolean) => {
      onOpenChange(nextOpen);
    },
    [onOpenChange],
  );

  const handleAplicar = useCallback(() => {
    onAplicar({
      estado: localEstado,
      prioridad: localPrioridad,
      mis_areas: false,
    });
    onOpenChange(false);
  }, [localEstado, localPrioridad, onAplicar, onOpenChange]);

  const handleLimpiar = useCallback(() => {
    setLocalEstado("");
    setLocalPrioridad("");
    onLimpiar();
    onOpenChange(false);
  }, [onLimpiar, onOpenChange]);

  return (
    <GenericModal open={open} onOpenChange={handleClose} preventClose={false}>
      <GenericModal.Content size="md">
        <GenericModal.Header
          title=""
          className="bg-primary/[0.03] border-b border-border px-6 py-5"
        >
          <div className="flex items-center gap-3 w-full">
            <div className="p-2 rounded-xl border border-primary/20 shadow-sm bg-primary/10 shrink-0">
              <Filter className="h-5 w-5 text-primary" />
            </div>
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                Filtros
              </span>
              <h2 className="text-2xl font-black tracking-tight text-foreground leading-tight">
                Filtrar solicitudes
              </h2>
              <p className="hidden sm:block text-sm text-muted-foreground leading-relaxed">
                Aplicá filtros para refinar el listado de solicitudes.
              </p>
            </div>
            <div className="w-9 shrink-0" aria-hidden="true" />
          </div>
        </GenericModal.Header>

        <GenericModal.Body className="space-y-5">
          {/* Estado */}
          <div className="space-y-2">
            <label
              htmlFor="filter-estado"
              className="text-sm font-semibold text-foreground"
            >
              Estado
            </label>
            <Select
              value={localEstado}
              onValueChange={(val) =>
                setLocalEstado(val as EstadoSolicitud | "")
              }
            >
              <SelectTrigger id="filter-estado" className="w-full">
                <SelectValue placeholder="Todos los estados" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">Todos los estados</SelectItem>
                <SelectItem value="REGISTRADA">Registrada</SelectItem>
                <SelectItem value="EN_TRAMITE">En Trámite</SelectItem>
                <SelectItem value="EN_GESTION">En Gestión</SelectItem>
                <SelectItem value="FINALIZADA">Finalizada</SelectItem>
                <SelectItem value="ANULADA">Anulada</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Prioridad */}
          <div className="space-y-2">
            <label
              htmlFor="filter-prioridad"
              className="text-sm font-semibold text-foreground"
            >
              Prioridad
            </label>
            <Select
              value={localPrioridad}
              onValueChange={(val) =>
                setLocalPrioridad(val as PrioridadSolicitud | "")
              }
            >
              <SelectTrigger id="filter-prioridad" className="w-full">
                <SelectValue placeholder="Todas las prioridades" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">Todas las prioridades</SelectItem>
                <SelectItem value="BAJA">Baja</SelectItem>
                <SelectItem value="MEDIA">Media</SelectItem>
                <SelectItem value="ALTA">Alta</SelectItem>
                <SelectItem value="URGENTE">Urgente</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </GenericModal.Body>

        <GenericModal.Footer className="px-6 py-4 bg-muted/30 border-t border-border">
          <div className="flex items-center justify-end gap-2">
            {hasActiveFilters ? (
              <Button
                type="button"
                variant="ghost"
                onClick={handleLimpiar}
                className="h-10 rounded-xl font-semibold text-destructive hover:text-destructive"
              >
                Limpiar filtros
              </Button>
            ) : (
              <div />
            )}
            <Button
              type="button"
              variant="outline"
              onClick={() => handleClose(false)}
              className="h-10 rounded-xl font-semibold"
            >
              Cancelar
            </Button>
            <Button
              type="button"
              onClick={handleAplicar}
              className="h-10 rounded-xl font-bold gap-1.5 btn-wine-gradient-hover"
            >
              Aplicar filtros
            </Button>
          </div>
        </GenericModal.Footer>

        <GenericModal.CloseX />
      </GenericModal.Content>
    </GenericModal>
  );
}
