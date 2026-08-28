"use client";

import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  Calendar,
  Clock,
  FileText,
  LinkIcon,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ESTADO_SOLICITUD,
  PRIORIDAD_SOLICITUD,
  TIPO_PARTICIPACION,
  type EstadoSolicitud,
  type PrioridadSolicitud,
  type TipoParticipacion,
} from "@/shared/constants/tramite.tokens";
import { useSolicitudDetail } from "@/features/tramites/hooks/useTramites";
import type { SolicitudDetail } from "@/features/tramites/schemas/tramite.schema";
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

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-PE", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

function getEstadoInstitucionalBadgeClass(
  estado: string | null,
): string {
  if (!estado) return "bg-muted text-muted-foreground border border-border";
  const token = ESTADO_SOLICITUD[estado as EstadoSolicitud];
  return token?.badgeClass ?? "bg-muted text-muted-foreground border border-border";
}

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
        <Button variant="outline" onClick={onBack}>
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

  const handleBack = () => router.back();

  if (isLoading) return <DetailSkeleton />;

  if (isError || !item) {
    return <EmptyState onBack={handleBack} />;
  }

  const title = item.expediente?.id_publico
    ? `Solicitud ${item.expediente.id_publico}`
    : "Detalle de Solicitud";

  return (
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
          <Badge className={ESTADO_SOLICITUD[item.estado as EstadoSolicitud].badgeClass}>
            {ESTADO_SOLICITUD[item.estado as EstadoSolicitud].label}
          </Badge>
          <Badge className={PRIORIDAD_SOLICITUD[item.prioridad as PrioridadSolicitud].badgeClass}>
            {PRIORIDAD_SOLICITUD[item.prioridad as PrioridadSolicitud].label}
          </Badge>
        </>
      }
    >
      {/* Información General */}
      <div className="app-card p-6 space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Información General
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Fecha de Registro</span>
            <span className="text-sm flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
              {formatDate(item.fecha_registro)}
            </span>
          </div>
          {item.fecha_inicio_gestion && (
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">Inicio de Gestión</span>
              <span className="text-sm flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                {formatDate(item.fecha_inicio_gestion)}
              </span>
            </div>
          )}
          {item.fecha_limite && (
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">Fecha Límite</span>
              <span className="text-sm flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                {formatDate(item.fecha_limite)}
              </span>
            </div>
          )}
          {item.observacion && (
            <div className="flex flex-col gap-1 sm:col-span-2">
              <span className="text-xs text-muted-foreground">Observación</span>
              <span className="text-sm">{item.observacion}</span>
            </div>
          )}
        </div>
      </div>

      {/* Expediente */}
      <div className="app-card p-6 space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Expediente
        </h2>
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-mono font-medium">
                {item.expediente?.id_publico ?? "—"}
              </span>
              {item.expediente?.asunto && (
                <span className="text-sm text-muted-foreground">
                  — {item.expediente.asunto}
                </span>
              )}
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="gap-2 shrink-0"
            onClick={() => router.push(`/expedientes/${item.expediente.id}`)}
          >
            <LinkIcon className="h-3.5 w-3.5" />
            Ver Expediente
          </Button>
        </div>
      </div>

      {/* Áreas y Períodos */}
      <div className="app-card p-6 space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Áreas / Períodos
        </h2>
        {item.asignaciones && item.asignaciones.length > 0 ? (
          <div className="space-y-6">
            {item.asignaciones.map((asignacion) => (
              <div key={asignacion.id} className="border rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">{asignacion.area_nombre}</span>
                  <Badge
                    className={
                      TIPO_PARTICIPACION[
                        (asignacion.periodos?.[0]?.tipo_participacion ?? "ADJUNTA") as TipoParticipacion
                      ]?.badgeClass ?? "bg-muted text-muted-foreground border border-border"
                    }
                  >
                    {TIPO_PARTICIPACION[
                      (asignacion.periodos?.[0]?.tipo_participacion ?? "ADJUNTA") as TipoParticipacion
                    ]?.label ?? asignacion.periodos?.[0]?.tipo_participacion ?? "—"}
                  </Badge>
                </div>

                {asignacion.observacion && (
                  <p className="text-xs text-muted-foreground italic">
                    {asignacion.observacion}
                  </p>
                )}

                {/* Períodos */}
                {asignacion.periodos && asignacion.periodos.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-xs text-muted-foreground uppercase tracking-wide">
                      Períodos
                    </span>
                    <div className="space-y-2">
                      {asignacion.periodos.map((periodo) => (
                        <div
                          key={periodo.id}
                          className="flex items-center justify-between bg-muted/50 rounded-md px-3 py-2 text-sm"
                        >
                          <div className="flex flex-col gap-0.5">
                            <span className="text-xs font-medium">
                              {periodo.tipo_participacion} — Ciclo {periodo.numero_ciclo}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {formatDate(periodo.fecha_inicio)}
                              {periodo.fecha_fin ? ` → ${formatDate(periodo.fecha_fin)}` : ""}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            {periodo.estado && (
                              <Badge className={getEstadoInstitucionalBadgeClass(periodo.estado)}>
                                {ESTADO_SOLICITUD[periodo.estado as EstadoSolicitud]?.label ?? periodo.estado}
                              </Badge>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Participantes */}
                {asignacion.participantes && asignacion.participantes.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-xs text-muted-foreground uppercase tracking-wide">
                      Participantes
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {asignacion.participantes
                        .filter(
                          (p, idx, arr) =>
                            arr.findIndex((a) => a.usuario_id === p.usuario_id) === idx,
                        )
                        .map((participacion) => (
                          <Badge
                            key={participacion.usuario_id}
                            className={
                              participacion.activo
                                ? "bg-primary/10 text-primary border border-primary/20"
                                : "bg-muted text-muted-foreground border border-border"
                            }
                          >
                            {participacion.usuario_nombres}
                            {participacion.rol ? ` (${participacion.rol})` : ""}
                          </Badge>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            No hay áreas asignadas a esta solicitud.
          </p>
        )}
      </div>

      {/* Historial */}
      <div className="app-card p-6 space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Historial
        </h2>
        {item.historial_global && item.historial_global.length > 0 ? (
          <ol className="relative border-l border-border ml-3 space-y-4">
            {[...item.historial_global].reverse().map((entry, idx) => (
              <li key={idx} className="ml-6">
                <div className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border-2 border-background bg-primary" />
                <div className="flex flex-col gap-0.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium">{entry.estado_nuevo}</span>
                    {entry.cambiado_por_nombres && (
                      <span className="text-xs text-muted-foreground">por {entry.cambiado_por_nombres}</span>
                    )}
                    <span className="text-xs text-muted-foreground ml-auto">
                      {formatDateTime(entry.fecha_cambio)}
                    </span>
                  </div>
                  {entry.observacion && (
                    <p className="text-xs text-muted-foreground">{entry.observacion}</p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            No hay historial registrado para esta solicitud.
          </p>
        )}
      </div>
    </PageWrapper>
  );
}
