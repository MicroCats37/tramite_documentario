"use client";

import { useQueryClient } from "@tanstack/react-query";
import { AlertCircle, FileText, MessageSquare } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageWrapper } from "@/components-app/page";
import type { PeriodoOperation } from "@/features/asignaciones/components";
import {
  IncorporarAreaModal,
  PeriodoOperacionModal,
} from "@/features/asignaciones/components";
import {
  useCambiarParticipacionPeriodo,
  useIniciarGestionPeriodo,
  useMarcarAsignacionErronea,
  useTomarPeriodoSolicitud,
} from "@/features/asignaciones/hooks";
import { useAuthStore } from "@/features/auth/store/auth.store";
import { ConversacionPanel } from "@/features/conversaciones/components/ConversacionPanel";
import { ExpedienteDetailModal } from "@/features/tramites/components/ExpedienteDetailModal";
import { FinalizarSolicitudModal } from "@/features/tramites/components/FinalizarSolicitudModal";
import { GestionOperativaSolicitud } from "@/features/tramites/components/GestionOperativaSolicitud";
import { SolicitudResumenEjecutivo } from "@/features/tramites/components/SolicitudResumenEjecutivo";
import { SolicitudWorkspaceLayout } from "@/features/tramites/components/SolicitudWorkspaceLayout";
import { TrazabilidadView } from "@/features/tramites/components/trazabilidad";
import { useSolicitudDetail } from "@/features/tramites/hooks/useTramites";
import {
  isUserAssignedToArea,
  normalizeId,
} from "@/features/tramites/utils/actionVisibility";
import { cn } from "@/lib/utils";
import { BUTTON_PRESETS } from "@/shared/constants/button.tokens";
import {
  ESTADO_SOLICITUD,
  type EstadoSolicitud,
  PRIORIDAD_SOLICITUD,
  type PrioridadSolicitud,
} from "@/shared/constants/tramite.tokens";

// ── Skeleton ───────────────────────────────────────────────────────────────────

function DetailSkeleton() {
  return (
    <div className="app-page">
      <div className="app-page-header ">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-9 w-32" />
      </div>
      <div className="space-y-4">
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    </div>
  );
}

// ── Empty State ───────────────────────────────────────────────────────────────

function EmptyState({ onBack }: { onBack: () => void }) {
  return (
    <PageWrapper
      title="Detalle de Solicitud"
      description="Detalle de la solicitud registrada"
      icon={<FileText className="h-6 w-6 text-primary" />}
      backHref="/solicitudes"
    >
      <div className="app-card flex flex-col items-center justify-center py-16 gap-4 text-center">
        <div className="p-4 bg-muted rounded-full">
          <AlertCircle className="h-8 w-8 text-muted-foreground" />
        </div>
        <div>
          <h3 className="font-semibold text-lg">Solicitud no encontrada</h3>
          <p className="text-sm text-muted-foreground mt-1">
            No se encontró la solicitud solicitada.
          </p>
        </div>
        <Button
          variant="outline"
          onClick={onBack}
          className={BUTTON_PRESETS.inline.secondary}
        >
          Volver a la bandeja
        </Button>
      </div>
    </PageWrapper>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function SolicitudDetallePage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: item, isLoading, isError } = useSolicitudDetail(id);
  const queryClient = useQueryClient();

  const tomarPeriodo = useTomarPeriodoSolicitud(item?.id ?? "");
  const iniciarGestion = useIniciarGestionPeriodo(item?.id ?? "");
  const marcarErronea = useMarcarAsignacionErronea(item?.id ?? "");
  const cambiarParticipacion = useCambiarParticipacionPeriodo(item?.id ?? "");

  const [finalizarModalOpen, setFinalizarModalOpen] = useState(false);
  const [operacionModalOpen, setOperacionModalOpen] = useState(false);
  const [incorporarAreaModalOpen, setIncorporarAreaModalOpen] = useState(false);
  const [expedienteModalOpen, setExpedienteModalOpen] = useState(false);
  const [activeOperation, setActiveOperation] = useState<string | null>(null);
  const [selectedOperation, setSelectedOperation] =
    useState<PeriodoOperation | null>(null);
  const [selectedPeriodoId, setSelectedPeriodoId] = useState<string | null>(
    null,
  );
  /**
   * Chat default state is viewport-dependent to avoid hydration mismatch:
   * - Desktop (>=1024px): open by default so the conversation is immediately visible.
   * - Mobile/tablet (<1024px): closed by default so the Solicitud is the initial view.
   * No localStorage — this is an initial viewport default, not a user preference.
   */
  const [chatOpen, setChatOpen] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia("(min-width: 1024px)").matches;
  });

  /**
   * Mobile: the conversation panel is a navigable, non-modal view. Pushing a
   * history entry lets the browser Back button restore the Solicitud view.
   * Desktop does not touch history — opening chat only reflows the layout.
   */
  useEffect(() => {
    if (!chatOpen) return;
    const isMobileViewport = window.matchMedia("(max-width: 1023px)").matches;
    if (!isMobileViewport) return;
    if (!window.history.state?.solicitudChatPanel) {
      window.history.pushState({ solicitudChatPanel: true }, "");
    }
    const onPopState = () => setChatOpen(false);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [chatOpen]);

  const handleToggleChat = () => {
    if (chatOpen) {
      setChatOpen(false);
      if (window.history.state?.solicitudChatPanel) {
        window.history.back();
      }
    } else {
      setChatOpen(true);
    }
  };

  const handleOperationSelect = (
    periodoId: string,
    operation: PeriodoOperation,
  ) => {
    setSelectedPeriodoId(periodoId);
    setSelectedOperation(operation);
    setOperacionModalOpen(true);
  };

  // ── Area gating ────────────────────────────────────────────────────────────────
  // Safely derive the set of area_ids the current user belongs to.
  // Failsafe: if user is missing, userAreaIds will be empty,
  // which disables area operations for everyone rather than crashing.
  const authUser = useAuthStore((s) => s.user);
  // Normalize user ID to handle both new shape (user.datos.id) and possible
  // stale cookies with old flat shape (user.id). The old shape existed before
  // the { datos, areas_asignadas_vigentes } migration; cookies may persist it.
  const currentUserId =
    authUser?.datos?.id ?? (authUser as unknown as { id?: string })?.id ?? null;
  // Normalize all area IDs to lowercase so Set.has() works reliably regardless
  // of backend returning uppercase or lowercase UUIDs.
  const userAreaIds = new Set<string>(
    authUser?.areas_asignadas_vigentes?.map((a) => normalizeId(a.area_id)) ??
      [],
  );

  const handleBack = () => router.back();

  const handleVerExpediente = () => setExpedienteModalOpen(true);

  if (isLoading) return <DetailSkeleton />;

  if (isError || !item) {
    return <EmptyState onBack={handleBack} />;
  }

  const title = item.expediente?.id_publico
    ? `Solicitud ${item.expediente.id_publico}`
    : "Detalle de Solicitud";

  // Gate "Finalizar" on whether user has at least one manageable period/area
  // with tipo_participacion=PRINCIPAL (principal area) AND that period is EN_GESTION
  // (i.e., the area has actually been "taken" / is being managed), and the
  // Solicitud is not finalized/anulada. Being a mere participant (ADJUNTA) or
  // associated user does not grant finalization authority — only principal areas
  // lead the closure. A non-member of a PRINCIPAL area cannot finalize either.
  const userCanFinalize = item.asignaciones.some((asignacion) => {
    const isMember = isUserAssignedToArea(asignacion.area_id, userAreaIds);
    const isPrincipal =
      asignacion.periodos?.[0]?.tipo_participacion === "PRINCIPAL";
    const hasEnGesPeriod = (asignacion.periodos ?? []).some(
      (p) => p.estado === "EN_GESTION",
    );
    // Require: user is a member of the area AND area is PRINCIPAL AND
    // at least one period is actively in EN_GESTION (not just PENDIENTE).
    return isMember && isPrincipal && hasEnGesPeriod;
  });

  // IDs of areas already assigned to this Solicitud — used to filter the
  // IncorporarAreaModal area selector.
  const assignedAreaIds = item.asignaciones.map((a) => a.area_id);

  return (
    <>
      <PageWrapper
        title={title}
        description="Detalle de la solicitud registrada"
        icon={<FileText className="h-6 w-6 text-primary" />}
        backHref="/solicitudes"
        breadcrumbs={[
          { label: "Solicitudes", href: "/solicitudes" },
          { label: title },
        ]}
        actions={
          <>
            <Badge
              className={
                ESTADO_SOLICITUD[item.estado as EstadoSolicitud].badgeClass
              }
            >
              {ESTADO_SOLICITUD[item.estado as EstadoSolicitud].label}
            </Badge>
            <Badge
              className={
                PRIORIDAD_SOLICITUD[item.prioridad as PrioridadSolicitud]
                  .badgeClass
              }
            >
              {PRIORIDAD_SOLICITUD[item.prioridad as PrioridadSolicitud].label}
            </Badge>

            {item.conversacion && (
              <Button
                variant="outline"
                size="sm"
                className={cn(BUTTON_PRESETS.compact.secondary, "text-xs")}
                aria-expanded={chatOpen}
                aria-controls="solicitud-conversacion-panel"
                onClick={handleToggleChat}
              >
                <MessageSquare className="h-3.5 w-3.5" />
                {chatOpen ? (
                  <>
                    <span className="hidden sm:inline">Conversación</span>
                    <span className="text-[10px] sm:hidden">Abierta</span>
                  </>
                ) : (
                  <>
                    <span className="hidden sm:inline">Abrir conversación</span>
                    <span className="sm:hidden">Conversación</span>
                  </>
                )}
              </Button>
            )}
          </>
        }
      >
        {/* Workspace: main content + integrated collapsible conversation panel */}
        <SolicitudWorkspaceLayout
          chatOpen={chatOpen}
          onCloseChat={handleToggleChat}
          chatPanel={({ onClose }) => (
            <ConversacionPanel
              conversacionId={item.conversacion?.id ?? null}
              solicitudId={item.id}
              currentUserId={currentUserId ?? undefined}
              disabled={!currentUserId}
              contextLabel={
                item.expediente?.id_publico
                  ? `Solicitud ${item.expediente.id_publico}`
                  : null
              }
              onClose={onClose}
            />
          )}
        >
          {/* Executive summary — under the header, above operational content */}
          <SolicitudResumenEjecutivo
            item={item}
            onVerExpedienteClick={handleVerExpediente}
          />

          {/* Operational management — user area/period actions, surfaced before traceability */}
          <GestionOperativaSolicitud
            item={item}
            currentUserId={currentUserId}
            userAreaIds={userAreaIds}
            tomarPeriodo={tomarPeriodo}
            iniciarGestion={iniciarGestion}
            onOperationSelect={handleOperationSelect}
            userCanFinalize={userCanFinalize}
            onFinalizar={() => setFinalizarModalOpen(true)}
            onIncorporarArea={() => setIncorporarAreaModalOpen(true)}
            activeOperation={activeOperation}
            onOperationStart={setActiveOperation}
          />

          {/* Flujo operativo — temporal graph + in-page contextual selection */}
          <TrazabilidadView
            solicitudId={item.id}
            fechaRegistro={item.fecha_registro}
            fechaCierre={item.fecha_cierre}
            estado={item.estado}
            idPublico={item.expediente?.id_publico ?? null}
          />
        </SolicitudWorkspaceLayout>
      </PageWrapper>

      <FinalizarSolicitudModal
        open={finalizarModalOpen}
        onOpenChange={setFinalizarModalOpen}
        solicitudId={item.id}
        disabled={!userCanFinalize}
      />
      <PeriodoOperacionModal
        open={operacionModalOpen}
        onOpenChange={(open) => {
          setOperacionModalOpen(open);
          if (!open) {
            // Clear active operation when modal is closed without success.
            // onSuccess already clears this; this covers backdrop/X/cancel close.
            setActiveOperation(null);
          }
        }}
        periodoId={selectedPeriodoId ?? ""}
        operation={selectedOperation}
        iniciarGestion={iniciarGestion}
        marcarErronea={marcarErronea}
        cambiarParticipacion={cambiarParticipacion}
        onSuccess={() => {
          setOperacionModalOpen(false);
          setSelectedOperation(null);
          setSelectedPeriodoId(null);
          setActiveOperation(null);
          queryClient.invalidateQueries({
            queryKey: ["solicitudes", "trazabilidad", item.id],
          });
        }}
      />
      <IncorporarAreaModal
        open={incorporarAreaModalOpen}
        onOpenChange={setIncorporarAreaModalOpen}
        solicitudId={item.id}
        assignedAreaIds={assignedAreaIds}
        onSuccess={() => {
          queryClient.invalidateQueries({
            queryKey: ["solicitudes", "detail", item.id],
          });
        }}
      />
      <ExpedienteDetailModal
        open={expedienteModalOpen}
        onOpenChange={setExpedienteModalOpen}
        expediente={item.expediente}
        solicitud={item}
      />
    </>
  );
}
