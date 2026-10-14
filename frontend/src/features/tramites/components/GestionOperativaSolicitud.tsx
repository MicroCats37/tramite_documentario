/**
 * GestionOperativaSolicitud — operational action section for Solicitud detail.
 *
 * Renders below ResumenEjecutivo and before TrazabilidadView.
 * Presentational-only: reuses existing mutations and modal state from the page.
 *
 * Visibility rules (presentation-only, no Guardian/rule changes):
 * - Tomar:       user area matches Solicitud area AND period operable AND user not active participant
 * - Iniciar:     user area matches OR active participant, period PENDIENTE, show inline tile
 * - MarcarErr:   user area matches OR active participant, period EN_GESTION, show inline tile
 * - CambiarPart: user area matches OR active participant, period EN_GESTION, show inline tile
 * - Finalizar:   current rule unchanged — appears in "Cierre de la solicitud" block
 *
 * All period operations (except Tomar) are rendered as inline tiles — NO dropdown.
 * TraceabilityInspector renders informational-only (actions removed from its footer).
 */
"use client";

import {
  AlertTriangle,
  ArrowLeftRight,
  CheckCircle,
  Hand,
  Info,
  Loader2,
  Play,
  Plus,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { useConfirmationDialog } from "@/components/confirmationDialog";
import { Button } from "@/components/ui/button";
import type { PeriodoOperation } from "@/features/asignaciones/components";
import {
  isActiveParticipantInPeriod,
  isUserAssignedToArea,
} from "@/features/tramites/utils/actionVisibility";
import { cn } from "@/lib/utils";
import {
  BUTTON_PRESETS,
  SPINNER_CLASS,
} from "@/shared/constants/button.tokens";
import {
  ESTADO_PERIODO,
  TIPO_PARTICIPACION,
  type TipoParticipacion,
} from "@/shared/constants/tramite.tokens";
import type { SolicitudDetail } from "../schemas/tramite.schema";

// ── View model types ───────────────────────────────────────────────────────────

export interface GestionOperativaProps {
  /** Full Solicitud detail (already loaded by parent page). */
  item: SolicitudDetail;
  /** Normalized current user ID (from auth store, already hydrated). */
  currentUserId: string | null;
  /** Normalized area IDs the current user belongs to (from auth store). */
  userAreaIds: Set<string>;
  /** Pre-wired tomar mutation from the page. */
  tomarPeriodo: {
    mutate: (periodoId: string, options?: { onSettled?: () => void }) => void;
    isPending: boolean;
  };
  /** Pre-wired iniciar gestion mutation from the page. */
  iniciarGestion: {
    mutate: (periodoId: string, options?: { onSettled?: () => void }) => void;
    isPending: boolean;
  };
  /** Pre-wired operation handler from the page. */
  onOperationSelect: (periodoId: string, operation: PeriodoOperation) => void;
  /** Whether the current user can finalize the Solicitud (already computed on page). */
  userCanFinalize: boolean;
  /** Handler to open the Finalizar modal. */
  onFinalizar: () => void;
  /** Handler to open the IncorporarAreaModal. */
  onIncorporarArea: () => void;
  /**
   * The currently active operation (e.g. "tomar", "iniciar-gestion", "marcar-erronea").
   * Used to show loading state on the correct button.
   */
  activeOperation: string | null;
  /**
   * Called when an operation button is clicked — tells the parent which
   * operation is starting so it can track isPending for loading UI.
   */
  onOperationStart: (op: string) => void;
}

// ── Derivation helpers ─────────────────────────────────────────────────────────

const CLOSED_PERIOD_STATES = new Set(["CERRADO", "FINALIZADO", "CANCELADO"]);

interface MatchedPeriod {
  periodoId: string;
  numeroCiclo: number;
  tipoParticipacion: string;
  estado: string;
  estadoLabel: string;
  /** True when period accepts operations (not closed/finalized/cancelled). */
  isOperable: boolean;
  /** True when current user is an active participant in this period. */
  isActiveParticipant: boolean;
  /** True when user belongs to area, not active participant, period operable → show Tomar. */
  showTomar: boolean;
  /** True when user area matches OR active participant, period operable → show operations. */
  showOperations: boolean;
}

interface MatchedArea {
  areaId: string;
  areaNombre: string;
  tipoParticipacion: TipoParticipacion;
  badgeClass: string;
  isMember: boolean;
  /** True when user is active participant in at least one period of this area. */
  hasActiveParticipation: boolean;
  matchedPeriods: MatchedPeriod[];
  /** All periods (matched or not) for informational display. */
  allPeriods: MatchedPeriod[];
}

/**
 * Derive matched areas and periods for the current user from SolicitudDetail.
 * No new fetches — all data comes from `item.asignaciones`.
 */
function deriveViewModel(
  item: SolicitudDetail,
  currentUserId: string | null,
  userAreaIds: Set<string>,
): {
  myManagedAreas: MatchedArea[];
  otherAssociatedAreas: MatchedArea[];
  allClosed: boolean;
  hasManagedOrAssociated: boolean;
  /** True when one of the user's areas is assigned to this solicitud. */
  hasUserAreaInSolicitud: boolean;
} {
  const myManagedAreas: MatchedArea[] = [];
  const otherAssociatedAreas: MatchedArea[] = [];
  let hasUserAreaInSolicitud = false;

  for (const asignacion of item.asignaciones) {
    const isMember = isUserAssignedToArea(asignacion.area_id, userAreaIds);
    if (isMember) {
      hasUserAreaInSolicitud = true;
    }
    const tipo = (asignacion.periodos?.[0]?.tipo_participacion ??
      "ADJUNTA") as TipoParticipacion;
    const token = TIPO_PARTICIPACION[tipo];

    const allPeriods: MatchedPeriod[] = (asignacion.periodos ?? []).map(
      (periodo) => {
        const isPeriodClosed = CLOSED_PERIOD_STATES.has(periodo.estado);
        const isActiveParticipant = isActiveParticipantInPeriod(
          asignacion.participantes,
          currentUserId,
        );
        // FIX: operations require isMember — active participation alone does NOT
        // grant management rights over other periods of the same area.
        const showTomar = isMember && !isActiveParticipant && !isPeriodClosed;
        const showOperations = isMember && !isPeriodClosed;

        return {
          periodoId: periodo.id,
          numeroCiclo: periodo.numero_ciclo,
          tipoParticipacion: periodo.tipo_participacion,
          estado: periodo.estado,
          estadoLabel:
            ESTADO_PERIODO[periodo.estado as keyof typeof ESTADO_PERIODO]
              ?.label ?? periodo.estado,
          isOperable: !isPeriodClosed,
          isActiveParticipant,
          showTomar,
          showOperations,
        };
      },
    );

    const matchedPeriods = allPeriods.filter(
      (p) => p.showTomar || p.showOperations,
    );

    const hasActiveParticipation = allPeriods.some(
      (p) => p.isActiveParticipant,
    );

    const areaEntry: MatchedArea = {
      areaId: asignacion.area_id,
      areaNombre: asignacion.area_nombre,
      tipoParticipacion: tipo,
      badgeClass:
        token?.badgeClass ??
        "bg-muted text-muted-foreground border border-border",
      isMember,
      hasActiveParticipation,
      matchedPeriods,
      allPeriods,
    };

    // Separate: member areas get full management; associated-only areas are informational.
    if (isMember) {
      myManagedAreas.push(areaEntry);
    } else if (hasActiveParticipation) {
      otherAssociatedAreas.push(areaEntry);
    }
  }

  const allManagedClosed = myManagedAreas.every((area) =>
    area.allPeriods.every((p) => !p.isOperable),
  );

  return {
    myManagedAreas,
    otherAssociatedAreas,
    allClosed: allManagedClosed,
    hasManagedOrAssociated:
      myManagedAreas.length > 0 || otherAssociatedAreas.length > 0,
    hasUserAreaInSolicitud,
  };
}

// ── Participation explanations ──────────────────────────────────────────────────

const PARTICIPATION_EXPLANATIONS: Record<string, string> = {
  PRINCIPAL: "El area lidera la atencion de esta solicitud.",
  ADJUNTA:
    "El area participa como soporte porque el asunto tambien le concierne.",
};

function getParticipacionExplicacion(tipo: string): string {
  return (
    PARTICIPATION_EXPLANATIONS[tipo] ?? "Tipo de participacion no especificado."
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

export function GestionOperativaSkeleton() {
  return (
    <div className="app-card p-5 lg:p-6 space-y-4">
      <div className="flex flex-col gap-2">
        <div className="h-4 w-40 rounded bg-muted animate-pulse" />
        <div className="h-3 w-72 rounded bg-muted animate-pulse" />
      </div>
      <div className="flex flex-wrap gap-2">
        <div className="h-8 w-32 rounded bg-muted animate-pulse" />
        <div className="h-8 w-28 rounded bg-muted animate-pulse" />
      </div>
      <div className="h-12 w-full rounded bg-muted animate-pulse" />
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export function GestionOperativaSolicitud({
  item,
  currentUserId,
  userAreaIds,
  tomarPeriodo,
  iniciarGestion,
  onOperationSelect,
  userCanFinalize,
  onFinalizar,
  onIncorporarArea,
  activeOperation,
  onOperationStart,
}: GestionOperativaProps) {
  const [tomandoPeriodoId, setTomandoPeriodoId] = useState<string | null>(null);
  const [iniciandoPeriodoId, setIniciandoPeriodoId] = useState<string | null>(
    null,
  );
  const { confirm, Dialog } = useConfirmationDialog();

  const {
    myManagedAreas,
    otherAssociatedAreas,
    allClosed,
    hasManagedOrAssociated,
    hasUserAreaInSolicitud,
  } = deriveViewModel(item, currentUserId, userAreaIds);

  // No auth user yet — show neutral skeleton to avoid flash of "consulta" state.
  if (!currentUserId) {
    return <GestionOperativaSkeleton />;
  }

  const isFinalizable =
    userCanFinalize &&
    item.estado !== "FINALIZADA" &&
    item.estado !== "ANULADA";

  // Only show "Cierre de la solicitud" when the user is actually managing
  // (has taken) at least one PRINCIPAL period — i.e., it is EN_GESTION.
  // PENDING principal periods do not qualify.
  const hasEnGesPrincipal = myManagedAreas.some(
    (area) =>
      area.isMember &&
      area.tipoParticipacion === "PRINCIPAL" &&
      area.allPeriods.some((p) => p.estado === "EN_GESTION"),
  );

  const canIncorporarArea =
    item.estado !== "FINALIZADA" &&
    item.estado !== "ANULADA" &&
    hasUserAreaInSolicitud;

  const handleTomar = async (periodoId: string) => {
    const ok = await confirm({
      title: "Tomar período",
      description:
        "Comenzarás a gestionar este período. Los demás usuarios del área verán que ya no está disponible para tomar.",
      consequences: [
        "Pasarás a ser quien gestiona este período",
        "El período se marcará como activo",
        "Después podrás finalizarlo, marcarlo como erróneo o cambiar la participación",
      ],
      confirmLabel: "Tomar",
      cancelLabel: "Cancelar",
      icon: Hand,
      variant: "default",
    });
    if (!ok) return;
    setTomandoPeriodoId(periodoId);
    onOperationStart("tomar");
    tomarPeriodo.mutate(periodoId, {
      onSettled: () => {
        setTomandoPeriodoId(null);
        onOperationStart("");
      },
    });
  };

  const handleIniciarGestion = async (periodoId: string) => {
    const ok = await confirm({
      title: "Iniciar gestión",
      description:
        "Pasarás este período a En Gestión. Después podrás finalizarlo, marcarlo como erróneo o cambiar la participación.",
      consequences: [
        "El período se moverá a En Gestión",
        "Podrás registrar respuestas y operar sobre el trámite",
        "El cambio se reflejará en la trazabilidad",
      ],
      confirmLabel: "Iniciar gestión",
      cancelLabel: "Cancelar",
      icon: Play,
      variant: "default",
    });
    if (!ok) return;
    setIniciandoPeriodoId(periodoId);
    onOperationStart(`iniciar-gestion-${periodoId}`);
    iniciarGestion.mutate(periodoId, {
      onSettled: () => {
        setIniciandoPeriodoId(null);
        onOperationStart("");
      },
    });
  };

  const handleOperation = (
    periodoId: string,
    op: "iniciar-gestion" | "marcar-erronea" | "cambiar-participacion",
  ) => {
    onOperationStart(`${periodoId}-${op}`);
    onOperationSelect(periodoId, op);
    // Parent handles isPending tracking via activeOperation; loading state
    // is derived from activeOperation === `${periodoId}-${op}` in each button.
  };

  // ── State 1: User has managed or associated areas ─────────────────────────
  if (hasManagedOrAssociated) {
    return (
      <>
        {Dialog}
        <section
          aria-labelledby="gestion-operativa-heading"
          className="app-card p-5 lg:p-6 space-y-6"
        >
          {/* Header */}
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex flex-col gap-1">
              <h2
                id="gestion-operativa-heading"
                className="text-sm font-semibold text-foreground"
              >
                Gestion operativa
              </h2>
              <p className="text-xs text-muted-foreground">
                Tus responsabilidades en esta solicitud
              </p>
            </div>
            {canIncorporarArea && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className={cn(
                  BUTTON_PRESETS.compact.secondary,
                  "text-xs shrink-0",
                )}
                onClick={onIncorporarArea}
              >
                <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                Incorporar area
              </Button>
            )}
          </div>

          {/* Mis áreas gestionables */}
          {myManagedAreas.length > 0 && (
            <div className="flex flex-col gap-3">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Mis areas gestionables
              </p>
              <div className="flex flex-col gap-2">
                {myManagedAreas.map((area) => (
                  <div
                    key={area.areaId}
                    className="flex flex-col gap-1.5 rounded-lg border border-border bg-card px-3 py-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-medium text-foreground">
                        {area.areaNombre}
                      </span>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span
                          className={cn(
                            "shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold",
                            area.badgeClass,
                          )}
                        >
                          {TIPO_PARTICIPACION[area.tipoParticipacion]?.label ??
                            area.tipoParticipacion}
                        </span>
                        {area.hasActiveParticipation && (
                          <span className="shrink-0 rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
                            Participas
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {getParticipacionExplicacion(area.tipoParticipacion)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Acciones disponibles — only for managed areas */}
          {myManagedAreas.some((a) => a.matchedPeriods.length > 0) ? (
            <div className="flex flex-col gap-3">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Acciones disponibles
              </p>
              <div className="flex flex-col gap-2">
                {myManagedAreas.map((area) =>
                  area.matchedPeriods.map((periodo) => (
                    <div
                      key={periodo.periodoId}
                      className="flex flex-col gap-3 rounded-lg border border-border bg-card px-3 py-3"
                    >
                      {/* Context label: area + ciclo + estado */}
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex min-w-0 flex-col gap-0.5">
                          <span className="truncate text-xs font-medium text-foreground">
                            {area.areaNombre}
                          </span>
                          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                            Participación {periodo.numeroCiclo}
                            <span className="text-muted-foreground/50">·</span>
                            <span
                              className={cn(
                                "rounded px-1 py-0.5 text-[10px]",
                                ESTADO_PERIODO[
                                  periodo.estado as keyof typeof ESTADO_PERIODO
                                ]?.badgeClass ??
                                  "bg-muted text-muted-foreground border border-border",
                              )}
                            >
                              {periodo.estadoLabel}
                            </span>
                            {periodo.isActiveParticipant && (
                              <span className="text-[10px] font-semibold text-primary">
                                · Tu participacion
                              </span>
                            )}
                          </span>
                        </div>
                        {periodo.showTomar && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className={cn(
                              BUTTON_PRESETS.compact.secondary,
                              "text-xs shrink-0",
                            )}
                            aria-label={`Gestionar participación ${periodo.numeroCiclo} de ${area.areaNombre}`}
                            onClick={() => handleTomar(periodo.periodoId)}
                            disabled={
                              tomandoPeriodoId === periodo.periodoId ||
                              tomarPeriodo.isPending
                            }
                          >
                            {tomandoPeriodoId === periodo.periodoId ||
                            activeOperation === "tomar" ? (
                              <Loader2 className={SPINNER_CLASS} />
                            ) : (
                              <Hand
                                className="h-3.5 w-3.5"
                                aria-hidden="true"
                              />
                            )}
                            Gestionar
                          </Button>
                        )}
                      </div>

                      {/* Iniciar gestion — only when user is active participant of a PENDIENTE period.
                          Migrated data may leave a participant assigned to a PENDIENTE period
                          without the period being moved to EN_GESTION; this action lets the user
                          advance the period state without losing their participation. */}
                      {periodo.isActiveParticipant &&
                        periodo.isOperable &&
                        periodo.estado === "PENDIENTE" && (
                          <div className="flex flex-col gap-0.5 min-w-0">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              className={cn(
                                BUTTON_PRESETS.compact.secondary,
                                "text-xs self-start",
                              )}
                              aria-label={`Iniciar gestión de participación ${periodo.numeroCiclo} de ${area.areaNombre}`}
                              onClick={() =>
                                handleIniciarGestion(periodo.periodoId)
                              }
                              disabled={
                                iniciandoPeriodoId === periodo.periodoId ||
                                activeOperation ===
                                  `iniciar-gestion-${periodo.periodoId}`
                              }
                            >
                              {iniciandoPeriodoId === periodo.periodoId ||
                              activeOperation ===
                                `iniciar-gestion-${periodo.periodoId}` ? (
                                <Loader2 className={SPINNER_CLASS} />
                              ) : (
                                <Play
                                  className="h-3.5 w-3.5"
                                  aria-hidden="true"
                                />
                              )}
                              Iniciar gestion
                            </Button>
                            <span className="text-[10px] text-muted-foreground leading-tight">
                              Mueve el período a En Gestión para empezar a
                              operar el trámite.
                            </span>
                          </div>
                        )}

                      {/* Compact secondary actions — only when period is EN_GESTION and user is eligible */}
                      {periodo.showOperations &&
                        periodo.estado === "EN_GESTION" && (
                          <div className="flex flex-wrap items-center gap-3">
                            {/* Marcar como erronea — compact destructive row */}
                            <div className="flex flex-col gap-0.5 min-w-0">
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className={cn(
                                  BUTTON_PRESETS.compact.secondary,
                                  "text-xs text-destructive border-destructive/30 hover:bg-destructive/10",
                                )}
                                disabled={
                                  activeOperation ===
                                  `${periodo.periodoId}-marcar-erronea`
                                }
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleOperation(
                                    periodo.periodoId,
                                    "marcar-erronea",
                                  );
                                }}
                              >
                                {activeOperation ===
                                `${periodo.periodoId}-marcar-erronea` ? (
                                  <Loader2 className={SPINNER_CLASS} />
                                ) : (
                                  <AlertTriangle
                                    className="h-3.5 w-3.5"
                                    aria-hidden="true"
                                  />
                                )}
                                Marcar erronea
                              </Button>
                              <span className="text-[10px] text-muted-foreground leading-tight">
                                Marca como incorrecta y solicita el motivo
                              </span>
                            </div>
                            {/* Cambiar participacion — compact row */}
                            <div className="flex flex-col gap-0.5 min-w-0">
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className={cn(
                                  BUTTON_PRESETS.compact.secondary,
                                  "text-xs",
                                )}
                                disabled={
                                  activeOperation ===
                                  `${periodo.periodoId}-cambiar-participacion`
                                }
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleOperation(
                                    periodo.periodoId,
                                    "cambiar-participacion",
                                  );
                                }}
                              >
                                {activeOperation ===
                                `${periodo.periodoId}-cambiar-participacion` ? (
                                  <Loader2 className={SPINNER_CLASS} />
                                ) : (
                                  <ArrowLeftRight
                                    className="h-3.5 w-3.5"
                                    aria-hidden="true"
                                  />
                                )}
                                Cambiar participacion
                              </Button>
                              <span className="text-[10px] text-muted-foreground leading-tight">
                                Cierra la participación y abre una nueva como
                                principal/adjunta
                              </span>
                            </div>
                          </div>
                        )}
                    </div>
                  )),
                )}
              </div>
            </div>
          ) : myManagedAreas.length > 0 ? (
            <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2.5">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">
                {allClosed
                  ? "No hay acciones pendientes. Los periodos de tus areas gestionables estan cerrados o finalizados."
                  : "No hay acciones pendientes para tus areas gestionables en este momento."}
              </p>
            </div>
          ) : null}

          {/* Otras áreas de la solicitud — read-only informational */}
          {otherAssociatedAreas.length > 0 && (
            <div className="flex flex-col gap-3">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Otras areas de la solicitud
              </p>
              <div className="flex flex-col gap-2">
                {otherAssociatedAreas.map((area) =>
                  area.allPeriods
                    .filter((p) => p.isActiveParticipant)
                    .map((periodo) => (
                      <div
                        key={`${area.areaId}-${periodo.periodoId}`}
                        className="flex flex-col gap-1.5 rounded-lg border border-border bg-muted/20 px-3 py-2"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-sm font-medium text-muted-foreground">
                            {area.areaNombre}
                          </span>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <span
                              className={cn(
                                "shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold",
                                area.badgeClass,
                              )}
                            >
                              {TIPO_PARTICIPACION[area.tipoParticipacion]
                                ?.label ?? area.tipoParticipacion}
                            </span>
                            <span className="shrink-0 rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
                              Participas
                            </span>
                          </div>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Solo tienes participación {periodo.numeroCiclo} en
                          esta área.
                        </p>
                      </div>
                    )),
                )}
              </div>
            </div>
          )}

          {/* Cierre de la solicitud — only when a principal period is actually being managed (EN_GESTION) */}
          {isFinalizable && hasEnGesPrincipal && (
            <div className="flex flex-col gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-3">
              <div className="flex items-start gap-2">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-destructive/20 bg-destructive/10">
                  <CheckCircle
                    className="h-4 w-4 text-destructive"
                    aria-hidden="true"
                  />
                </div>
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span className="text-xs font-semibold text-destructive">
                    Cierre de la solicitud
                  </span>
                  <span className="text-xs text-muted-foreground">
                    Registrar la respuesta formal institucional y cerrar la
                    solicitud. Esta accion no se puede deshacer.
                  </span>
                </div>
              </div>
              <Button
                type="button"
                variant="destructive"
                size="sm"
                className={cn(
                  BUTTON_PRESETS.inline.destructive,
                  "text-xs self-start",
                )}
                onClick={onFinalizar}
              >
                <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
                Finalizar Solicitud
              </Button>
            </div>
          )}
        </section>
      </>
    );
  }

  // ── State 2: No managed or associated areas — consulta view ───────────────
  return (
    <>
      {Dialog}
      <section
        aria-labelledby="gestion-operativa-heading"
        className="app-card p-5 lg:p-6"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <h2
              id="gestion-operativa-heading"
              className="text-sm font-semibold text-foreground"
            >
              Gestion operativa
            </h2>
            <p className="text-xs text-muted-foreground">
              Tus responsabilidades en esta solicitud
            </p>
          </div>
          {canIncorporarArea && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className={cn(
                BUTTON_PRESETS.compact.secondary,
                "text-xs shrink-0",
              )}
              onClick={onIncorporarArea}
            >
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              Incorporar area
            </Button>
          )}
        </div>
        <div className="mt-3 flex items-start gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2.5">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <p className="text-xs text-muted-foreground">
            Vista de consulta. No tienes areas gestionables ni participacion
            activa en esta solicitud.
          </p>
        </div>
      </section>
    </>
  );
}
