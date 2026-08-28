// genericForm/inputs/InputAreaDistribution.tsx
// Smart Field para distribución de áreas institucionales.
// Organiza áreas en secciones: Áreas Principales y Áreas Adjuntas.
// Cada área se muestra como un card con selector para cambiar tipo.
// NO contiene validación interna — Zod la maneja.
// Usa useController de RHF + useAreas().

"use client";

import { Building2, Plus, X } from "lucide-react";
import type React from "react";
import { useState } from "react";
import { useController } from "react-hook-form";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { cn } from "@/lib/utils";
import { TIPO_PARTICIPACION, type TipoParticipacion } from "@/shared/constants/tramite.tokens";
import { useAreas, type Area } from "@/features/tramites/hooks/useAreas";
import type { InputComponentProps } from "./types";

// ── Tipos internos ─────────────────────────────────────────────────────────────

export interface AreaDistribucionItem {
  area_id: string;
  tipo_participacion: TipoParticipacion;
  observacion?: string | null;
}

export interface InputAreaDistributionProps extends InputComponentProps {
  /** Placeholder para el selector de área */
  selectorPlaceholder?: string;
}

// ── Utilidades ─────────────────────────────────────────────────────────────────

function buildInitialValue(value: unknown): AreaDistribucionItem[] {
  if (!value) return [];
  if (Array.isArray(value)) return value as AreaDistribucionItem[];
  return [];
}

// ── Sub-componente: AreaCard ───────────────────────────────────────────────────

interface AreaCardProps {
  item: AreaDistribucionItem;
  areaNombre: string;
  onRemove: (areaId: string) => void;
  onTipoChange: (areaId: string, tipo: TipoParticipacion) => void;
}

const AreaCard: React.FC<AreaCardProps> = ({
  item,
  areaNombre,
  onRemove,
  onTipoChange,
}) => {
  const tipoToken = TIPO_PARTICIPACION[item.tipo_participacion];

  return (
    <div className="flex items-center gap-3 rounded-lg border p-3 bg-muted/20">
      <div className="flex-shrink-0 text-muted-foreground">
        <Building2 className="w-4 h-4" />
      </div>

      <div className="flex-1 min-w-0">
        <p
          className="text-sm font-medium truncate"
          title={areaNombre}
        >
          {areaNombre}
        </p>
      </div>

      {/* Mini-select para cambiar tipo */}
      <Select
        value={item.tipo_participacion}
        onValueChange={(val) => onTipoChange(item.area_id, val as TipoParticipacion)}
      >
        <SelectTrigger
          className={cn(
            "h-7 w-auto min-w-[100px] text-xs gap-1.5",
            tipoToken.badgeClass,
          )}
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent position="item-aligned">
          <SelectItem value="PRINCIPAL">
            <span className={cn("inline-flex items-center gap-1", TIPO_PARTICIPACION.PRINCIPAL.badgeClass)}>
              Principal
            </span>
          </SelectItem>
          <SelectItem value="ADJUNTA">
            <span className={cn("inline-flex items-center gap-1", TIPO_PARTICIPACION.ADJUNTA.badgeClass)}>
              Adjunta
            </span>
          </SelectItem>
        </SelectContent>
      </Select>

      {/* Botón quitar */}
      <Button
        type="button"
        variant="ghost"
        size="icon-xs"
        className="flex-shrink-0 text-muted-foreground hover:text-destructive"
        onClick={() => onRemove(item.area_id)}
        title="Quitar área"
      >
        <X className="w-3.5 h-3.5" />
      </Button>
    </div>
  );
};

// ── Componente principal ───────────────────────────────────────────────────────

export const InputAreaDistribution: React.FC<InputAreaDistributionProps> = ({
  field,
  control,
  id,
  hideErrorMessage,
  error,
  selectorPlaceholder = "Seleccione un área...",
}) => {
  const { areas, isLoading, isError } = useAreas();
  const [selectorOpen, setSelectorOpen] = useState(false);

  const {
    field: { onChange, value },
  } = useController({ name: field.name, control });

  const selectedItems: AreaDistribucionItem[] = buildInitialValue(value);
  const internalId = id || `area-distribution-${field.name}`;

  // Separar principales y adjuntas
  const areasPrincipales = selectedItems.filter(
    (item) => item.tipo_participacion === "PRINCIPAL",
  );
  const areasAdjuntas = selectedItems.filter(
    (item) => item.tipo_participacion === "ADJUNTA",
  );

  const handleAddArea = (areaId: string) => {
    // No duplicados
    if (selectedItems.some((item) => item.area_id === areaId)) {
      setSelectorOpen(false);
      return;
    }
    // Si ya existe un principal, la nueva área por defecto es ADJUNTA
    const hasPrincipal = selectedItems.some(
      (item) => item.tipo_participacion === "PRINCIPAL",
    );
    onChange([
      ...selectedItems,
      {
        area_id: areaId,
        tipo_participacion: hasPrincipal ? "ADJUNTA" : "PRINCIPAL",
        observacion: null,
      },
    ]);
    setSelectorOpen(false);
  };

  const handleRemoveArea = (areaId: string) => {
    onChange(selectedItems.filter((item) => item.area_id !== areaId));
  };

  const handleTipoChange = (areaId: string, tipo: TipoParticipacion) => {
    onChange(
      selectedItems.map((item) =>
        item.area_id === areaId
          ? { ...item, tipo_participacion: tipo }
          : item,
      ),
    );
  };

  const getAreaNombre = (areaId: string): string => {
    const area = areas.find((a) => a.id === areaId);
    return area?.nombre ?? areaId;
  };

  return (
    <div className="space-y-4">
      {/* Contenedor principal */}
      <div className="rounded-lg border border-dashed p-4 space-y-4">
        <div className="flex items-center gap-2">
          <Building2 className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium">Distribución de Áreas</span>
        </div>

        {/* ── Sección: Áreas Principales ── */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold">
              Áreas Principales
              {areasPrincipales.length > 0 && (
                <span className="ml-1 text-xs font-normal text-muted-foreground">
                  ({areasPrincipales.length})
                </span>
              )}
            </span>
          </div>

          {areasPrincipales.length === 0 ? (
            <p className="text-sm text-muted-foreground py-2">
              No hay áreas principales añadidas
            </p>
          ) : (
            <div className="grid gap-2">
              {areasPrincipales.map((item) => (
                <AreaCard
                  key={item.area_id}
                  item={item}
                  areaNombre={getAreaNombre(item.area_id)}
                  onRemove={handleRemoveArea}
                  onTipoChange={handleTipoChange}
                />
              ))}
            </div>
          )}
        </div>

        {/* ── Sección: Áreas Adjuntas ── */}
        <div className="space-y-2 pt-2 border-t">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold">
              Áreas Adjuntas
              {areasAdjuntas.length > 0 && (
                <span className="ml-1 text-xs font-normal text-muted-foreground">
                  ({areasAdjuntas.length})
                </span>
              )}
            </span>
          </div>

          {areasAdjuntas.length === 0 ? (
            <p className="text-sm text-muted-foreground py-2">
              No hay áreas adjuntas añadidas
            </p>
          ) : (
            <div className="grid gap-2">
              {areasAdjuntas.map((item) => (
                <AreaCard
                  key={item.area_id}
                  item={item}
                  areaNombre={getAreaNombre(item.area_id)}
                  onRemove={handleRemoveArea}
                  onTipoChange={handleTipoChange}
                />
              ))}
            </div>
          )}
        </div>

        {/* ── Selector + botón añadir ── */}
        <div className="flex gap-2 items-start pt-2 border-t">
          <div className="flex-1">
            {isLoading ? (
              <SearchableSelect
                id={internalId}
                label=""
                value={null}
                onValueChange={() => {}}
                options={[]}
                placeholder="Cargando áreas..."
                disabled
                showLabel={false}
                hideErrorMessage
              />
            ) : isError ? (
              <SearchableSelect
                id={internalId}
                label=""
                value={null}
                onValueChange={() => {}}
                options={[]}
                placeholder="Error al cargar áreas"
                disabled
                showLabel={false}
                hideErrorMessage
              />
            ) : (
              <SearchableSelect
                id={internalId}
                label=""
                value={null}
                onValueChange={(value) => {
                  if (value) handleAddArea(value);
                }}
                options={areas.map((area: Area) => ({
                  value: area.id,
                  label: area.descripcion
                    ? `${area.nombre} — ${area.descripcion}`
                    : area.nombre,
                }))}
                placeholder={selectorPlaceholder}
                disabled={isLoading || isError}
                showLabel={false}
                hideErrorMessage
              />
            )}
          </div>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              // Disparar el Popover del SearchableSelect abriendo el trigger
              const trigger = document.getElementById(internalId);
              trigger?.click();
            }}
            className="gap-2 flex-shrink-0"
            disabled={isLoading || isError}
          >
            <Plus className="w-4 h-4" />
            Añadir área
          </Button>
        </div>
      </div>

      {/* Error — solo si hideErrorMessage es false */}
      {!hideErrorMessage && error && (
        <p className="text-sm text-destructive font-medium">{error.message}</p>
      )}
    </div>
  );
};
