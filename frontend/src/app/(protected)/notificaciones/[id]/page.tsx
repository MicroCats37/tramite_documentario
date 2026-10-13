/**
 * Detalle de Notificación — pantalla completa con contexto enriquecido.
 * Ruta: /notificaciones/[id]
 *
 * Flujo:
 * 1. Obtiene el detalle de la notificación via useNotificacionDetalle.
 * 2. Llama POST /notificaciones/{id}/vista al montar (useMarkVista).
 * 3. Muestra pantalla de detalle con título, descripción, contexto.
 * 4. Botón "Ver solicitud" → POST /notificaciones/{id}/abrir → navegar a solicitud.
 * 5. Siempre disponible: enlace de retorno a /notificaciones.
 */
"use client";

import {
  AlertCircle,
  ArrowLeft,
  Bell,
  Calendar,
  ExternalLink,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageWrapper } from "@/components-app/page";
import {
  useAbrirNotificacion,
  useMarkVista,
  useNotificacionDetalle,
} from "@/features/notificaciones/hooks/useNotificaciones";
import type {
  EstadoNotificacionIndividual,
  NotificationSolicitudDetailData,
} from "@/features/notificaciones/schemas/notificacion.schema";
import { ESTADO_NOTIFICACION } from "@/shared/constants/tramite.tokens";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-PE", {
      day: "2-digit",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

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

function DetailSkeleton() {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2 flex-1">
          <Skeleton className="h-6 w-3/4" />
          <Skeleton className="h-4 w-1/4" />
        </div>
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      {/* Body */}
      <div className="space-y-3">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-4 w-1/3" />
      </div>
      {/* Actions */}
      <Skeleton className="h-9 w-40" />
    </div>
  );
}

// ── FileIcon (inline SVG para consistencia) ───────────────────────────────────

function FileIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      role="img"
      aria-label="Archivo de solicitud"
      className={className}
    >
      <title>Archivo de solicitud</title>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14,2 14,8 20,8" />
    </svg>
  );
}

// ── Detail Card ────────────────────────────────────────────────────────────────

interface DetailCardProps {
  item: NotificationSolicitudDetailData;
}

function DetailCard({ item }: DetailCardProps) {
  const router = useRouter();

  const { mutateAsync: abrirNotificacion } = useAbrirNotificacion();

  const estadoToken =
    ESTADO_NOTIFICACION[item.estado_individual as EstadoNotificacionIndividual];
  const hasSolicitud = Boolean(item.solicitud_id);

  const handleVerSolicitud = async () => {
    if (!item.solicitud_id) return;
    try {
      await abrirNotificacion(item.id);
    } catch {
      toast.error("No se pudo abrir la notificación");
      // Still navigate even if abrir fails
    }
    router.push(`/solicitudes/${item.solicitud_id}`);
  };

  return (
    <div className="app-card p-6 space-y-5">
      {/* Header: título + badge + tipo */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1 min-w-0">
          <h2 className="text-base font-semibold leading-snug">
            {item.titulo}
          </h2>
          <p className="text-sm text-muted-foreground">
            {item.evento ?? "Notificación"}
          </p>
        </div>
        <Badge className={estadoToken.badgeClass}>{estadoToken.label}</Badge>
      </div>

      {/* Descripción completa */}
      {item.mensaje && (
        <p className="text-sm text-foreground leading-relaxed bg-muted/50 rounded-md p-3 border">
          {item.mensaje}
        </p>
      )}

      {/* Metadatos en grid */}
      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
        <div className="flex items-start gap-2">
          <Calendar className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
          <div>
            <dt className="text-xs text-muted-foreground">Fecha del evento</dt>
            <dd className="font-medium">{formatDate(item.ocurrido_en)}</dd>
          </div>
        </div>

        <div className="flex items-start gap-2">
          <Bell className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
          <div>
            <dt className="text-xs text-muted-foreground">Área</dt>
            <dd className="font-medium">{item.area_nombre}</dd>
          </div>
        </div>

        {item.expediente_publico?.id_publico && (
          <div className="flex items-start gap-2">
            <FileIcon className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
            <div>
              <dt className="text-xs text-muted-foreground">
                Expediente / Solicitud
              </dt>
              <dd className="font-medium font-mono">
                {item.expediente_publico.id_publico}
              </dd>
            </div>
          </div>
        )}

        {item.solicitud_asunto && (
          <div className="col-span-2">
            <dt className="text-xs text-muted-foreground">Asunto</dt>
            <dd className="font-medium text-sm">{item.solicitud_asunto}</dd>
          </div>
        )}

        {item.periodo?.numero_ciclo != null && (
          <div>
            <dt className="text-xs text-muted-foreground">Participación</dt>
            <dd className="font-medium">{item.periodo.numero_ciclo}</dd>
          </div>
        )}

        {item.periodo?.esta_abierto != null && (
          <div>
            <dt className="text-xs text-muted-foreground">Período</dt>
            <dd
              className={`font-medium ${
                item.periodo.esta_abierto
                  ? "text-green-600"
                  : "text-muted-foreground"
              }`}
            >
              {item.periodo.esta_abierto ? "Activo" : "Cerrado"}
            </dd>
          </div>
        )}

        {item.participo != null && (
          <div>
            <dt className="text-xs text-muted-foreground">Participación</dt>
            <dd
              className={`font-medium ${
                item.participo ? "text-primary" : "text-muted-foreground"
              }`}
            >
              {item.participo ? "Participas" : "No participas"}
            </dd>
          </div>
        )}
      </dl>

      {/* Divider */}
      <div className="border-t" />

      {/* Acciones */}
      <div className="flex flex-wrap items-center gap-2">
        {hasSolicitud && (
          <Button
            variant="default"
            size="sm"
            className="gap-1.5"
            onClick={handleVerSolicitud}
          >
            <ExternalLink className="h-4 w-4" />
            Ver solicitud
          </Button>
        )}

        <Button
          variant="ghost"
          size="sm"
          className="gap-1.5 ml-auto"
          onClick={() => router.push("/notificaciones")}
        >
          <ArrowLeft className="h-4 w-4" />
          Volver a notificaciones
        </Button>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function NotificacionDetallePage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const {
    data: notificacion,
    isLoading,
    isError,
    error,
  } = useNotificacionDetalle(id);

  const { mutateAsync: markVista } = useMarkVista();

  // Marcar como vista al montar — una sola vez cuando el id está disponible.
  const vistaCalled = useRef(false);
  useEffect(() => {
    if (!id || !notificacion || vistaCalled.current) return;
    vistaCalled.current = true;
    markVista(id).catch(() => {
      // Silenciamos — la notificación se muestra de todas formas
    });
  }, [id, notificacion, markVista]);

  // ── Loading ────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <PageWrapper
        title="Notificación"
        description="Cargando detalle…"
        icon={<Bell className="h-6 w-6 text-primary" />}
        backHref="/notificaciones"
      >
        <DetailSkeleton />
      </PageWrapper>
    );
  }

  // ── Error ──────────────────────────────────────────────────────────────────
  if (isError || !notificacion) {
    const errorMessage =
      error instanceof Error
        ? error.message
        : "No se pudo cargar la notificación";
    return (
      <PageWrapper
        title="Notificación"
        description="Detalle de la notificación"
        icon={<Bell className="h-6 w-6 text-primary" />}
        backHref="/notificaciones"
      >
        <div className="app-card flex flex-col items-center justify-center py-16 gap-4 text-center">
          <div className="p-4 bg-destructive/10 rounded-full">
            <AlertCircle className="h-8 w-8 text-destructive" />
          </div>
          <div>
            <h3 className="font-semibold text-lg">Error al abrir</h3>
            <p className="text-sm text-muted-foreground mt-1">{errorMessage}</p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => router.push("/notificaciones")}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Volver a notificaciones
            </Button>
            <Button variant="ghost" onClick={() => router.refresh()}>
              Reintentar
            </Button>
          </div>
        </div>
      </PageWrapper>
    );
  }

  // ── Detail ─────────────────────────────────────────────────────────────────
  return (
    <PageWrapper
      title="Notificación"
      description={`Notificación del ${formatDateTime(notificacion.ocurrido_en)}`}
      icon={<Bell className="h-6 w-6 text-primary" />}
      backHref="/notificaciones"
    >
      <DetailCard item={notificacion} />
    </PageWrapper>
  );
}
