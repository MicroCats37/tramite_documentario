/**
 * SolicitudDetailModal — premium quick-view modal for Solicitud.
 *
 * Layout (matches the quick-view target):
 * - Header band: subtle wine gradient, FileText icon block, tipo_persona eyebrow +
 *   expediente.id_publico title + relative time, status pill, X close.
 * - Body: 2-column responsive grid (Solicitante + Expediente | Gestión del Trámite wine section).
 * - Footer: Imprimir | Cerrar | Ver Detalles Completos.
 *
 * Uses GenericModal compound pattern (aligns with the app modal/form line).
 * Extra detail fields (creado_por_nombres, fecha_cierre, historial) live on the
 * detail page reachable via "Ver Detalles Completos".
 */
"use client";

import {
  ArrowRight,
  Briefcase,
  Building2,
  Clock,
  ExternalLink,
  FileText,
  FolderOpen,
  Mail,
  Paperclip,
  Phone,
  Printer,
  User,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { BUTTON_PRESETS } from "@/shared/constants/button.tokens";
import {
  ESTADO_SOLICITUD,
  type EstadoSolicitud,
  TIPO_ARCHIVO,
  type TipoArchivo,
} from "@/shared/constants/tramite.tokens";
import type { SolicitudItem } from "../schemas/tramite.schema";
import { PrintPreviewModal } from "./PrintPreviewModal";
import { buildSolicitudPrintHTML } from "./printExpediente";
import { SolicitudPrintPreview } from "./SolicitudPrintPreview";

function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) return "—";
  try {
    const date = value instanceof Date ? value : new Date(value);
    return date.toLocaleString("es-PE", {
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

/**
 * Format an ISO timestamp into a Spanish relative-time phrase.
 * Past < 1 min → "hace un momento".
 * Past < 60 min → "hace X minutos".
 * Past < 24 h → "hace X horas".
 * Past < 30 d → "hace X días".
 * Past < 365 d → "hace X meses".
 * Past ≥ 365 d → "hace X años".
 * Future mirrors with "en X …".
 * Invalid / null / undefined → "—".
 */
function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const target = new Date(iso).getTime();
  if (Number.isNaN(target)) return "—";
  const diffMs = Date.now() - target;
  const future = diffMs < 0;
  const absMs = Math.abs(diffMs);
  const seconds = Math.floor(absMs / 1000);
  if (seconds < 60) return "hace un momento";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60)
    return future ? `en ${minutes} minutos` : `hace ${minutes} minutos`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return future ? `en ${hours} horas` : `hace ${hours} horas`;
  const days = Math.floor(hours / 24);
  if (days < 30) return future ? `en ${days} días` : `hace ${days} días`;
  const months = Math.floor(days / 30);
  if (months < 12)
    return future ? `en ${months} meses` : `hace ${months} meses`;
  const years = Math.floor(months / 12);
  return future ? `en ${years} años` : `hace ${years} años`;
}

interface SolicitudDetailModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: SolicitudItem | null;
}

export function SolicitudDetailModal({
  open,
  onOpenChange,
  item,
}: SolicitudDetailModalProps) {
  const router = useRouter();
  const [printOpen, setPrintOpen] = useState(false);
  const [printHtml, setPrintHtml] = useState("");

  if (!item) return null;

  const { expediente } = item;

  // ── Derived data ────────────────────────────────────────────────────────────
  const estadoToken = ESTADO_SOLICITUD[item.estado as EstadoSolicitud];

  const nombreCompleto =
    expediente.razon_social ||
    [expediente.nombres, expediente.apellidos].filter(Boolean).join(" ") ||
    "—";

  // Fecha límite / vencida (mirrors SolicitudCard logic)
  const fechaLimite = item.fecha_limite ? new Date(item.fecha_limite) : null;
  const vencida =
    fechaLimite !== null &&
    fechaLimite < new Date() &&
    item.estado !== "FINALIZADA";

  const archivos = expediente.archivos ?? [];

  // Relative-time copy
  const relativeRegistered = formatRelativeTime(expediente.fecha_registro);

  // ── Handlers ────────────────────────────────────────────────────────────────
  const handlePrint = () => {
    setPrintHtml(buildSolicitudPrintHTML(item));
    setPrintOpen(true);
  };

  const handleVerDetalles = () => {
    onOpenChange(false);
    router.push(`/solicitudes/${item.id}`);
  };

  return (
    <>
      <GenericModal open={open} onOpenChange={onOpenChange}>
        <GenericModal.Content
          size="xl"
          className="solicitud-modal-shell w-[min(920px,calc(100vw-2rem))] max-w-[min(920px,calc(100vw-2rem))]"
        >
          {/* ── Header — matches the form modal pattern (SolicitudFormModal:242-260) ── */}
          <div className="solicitud-modal-header bg-gradient-to-r from-primary/5 via-primary/[0.02] to-transparent border-b border-border px-6 py-5 sm:px-8">
            <div className="flex items-center gap-3 w-full">
              <div className="p-2 sm:p-2.5 bg-primary/10 rounded-xl sm:rounded-2xl border border-primary/20 shadow-sm shrink-0">
                <FileText className="h-5 w-5 text-primary" />
              </div>
              <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                  Mesa de Partes
                </span>
                <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground leading-tight break-all">
                  {expediente.id_publico}
                </h2>
                <p className="hidden sm:block max-w-prose text-pretty line-clamp-2 text-sm text-muted-foreground leading-relaxed">
                  Solicitud #{expediente.id_publico} · Registrado{" "}
                  {relativeRegistered}
                </p>
              </div>
            </div>
          </div>

          {/* ── Body ─────────────────────────────────────────────────────── */}
          <GenericModal.Body className="solicitud-modal-body flex-1 overflow-y-auto">
            <div className="min-w-0 px-6 py-5">
              <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] gap-5">
                {/* ── Left column ────────────────────────────────────────── */}
                <div className="space-y-5">
                  {/* Solicitante card */}
                  <section className="solicitud-modal-card rounded-xl border border-border/50 bg-card p-5 space-y-4">
                    <header className="flex items-center gap-2">
                      <User className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                        Solicitante
                      </span>
                    </header>
                    <div>
                      <p className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                        <Building2 className="h-3 w-3" />
                        Razón Social
                      </p>
                      <p className="mt-1 text-base font-bold leading-tight text-foreground">
                        {nombreCompleto}
                      </p>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 border-t border-border pt-4">
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Teléfono
                        </p>
                        <p className="mt-1 flex items-center gap-1.5 text-sm text-foreground">
                          <Phone className="h-3 w-3 text-muted-foreground shrink-0" />
                          {expediente.telefono || "—"}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          E-mail
                        </p>
                        <p className="mt-1 flex items-center gap-1.5 text-sm text-foreground break-all">
                          <Mail className="h-3 w-3 text-muted-foreground shrink-0" />
                          {expediente.correo || "—"}
                        </p>
                      </div>
                    </div>
                  </section>

                  {/* Expediente card */}
                  <section className="solicitud-modal-card rounded-xl border border-border/50 bg-card p-5 space-y-4">
                    <header className="flex items-center gap-2">
                      <FolderOpen className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                        Expediente
                      </span>
                    </header>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                        Asunto
                      </p>
                      <p className="mt-1 text-sm font-semibold leading-snug line-clamp-2 text-foreground">
                        {expediente.asunto || "—"}
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-4 border-t border-border pt-4">
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          N° Documento
                        </p>
                        <p className="mt-1 font-mono text-sm font-semibold text-foreground break-all">
                          {expediente.id_publico}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Folios
                        </p>
                        <p className="mt-1 text-sm font-semibold text-foreground">
                          {expediente.numero_folios}
                        </p>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 border-t border-border pt-4">
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Fecha Registro
                        </p>
                        <p className="mt-1 text-sm font-semibold text-foreground">
                          {formatDateTime(expediente.fecha_registro)}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                          Expediente CIP
                        </p>
                        <p className="mt-1 text-sm font-semibold text-foreground">
                          {expediente.cip || "—"}
                        </p>
                      </div>
                    </div>

                    {/* Adjuntos subsection */}
                    <div className="border-t border-border pt-4 space-y-2">
                      <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                        Adjuntos
                      </p>
                      {archivos.length > 0 ? (
                        <div className="space-y-1.5">
                          {archivos.map((archivo) => (
                            <div
                              key={archivo.id}
                              className="flex items-center justify-between gap-2 rounded-lg border border-border bg-background px-3 py-2"
                            >
                              <div className="flex items-center gap-2 min-w-0 flex-1">
                                <Paperclip className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                                <span
                                  className="truncate text-sm font-medium text-foreground"
                                  title={archivo.nombre_original}
                                >
                                  {archivo.nombre_original}
                                </span>
                                <span
                                  className={cn(
                                    "shrink-0 inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-medium",
                                    TIPO_ARCHIVO[
                                      archivo.tipo_archivo as TipoArchivo
                                    ]?.badgeClass ??
                                      "bg-muted text-muted-foreground border-border",
                                  )}
                                >
                                  {TIPO_ARCHIVO[
                                    archivo.tipo_archivo as TipoArchivo
                                  ]?.label ?? archivo.tipo_archivo}
                                </span>
                              </div>
                              <a
                                href={archivo.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                title="Abrir archivo"
                                aria-label={`Abrir ${archivo.nombre_original}`}
                                className="shrink-0 inline-flex h-7 w-7 items-center justify-center rounded-md border border-border bg-card text-muted-foreground hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-colors print-hidden"
                              >
                                <ExternalLink className="h-3.5 w-3.5" />
                              </a>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs italic text-muted-foreground">
                          Sin archivos adjuntos
                        </p>
                      )}
                    </div>
                  </section>
                </div>

                {/* ── Right column ───────────────────────────────────────── */}
                <div className="space-y-5">
                  {/* Gestión del trámite — wine-tinted */}
                  <section className="solicitud-modal-card rounded-xl border border-primary/20 bg-primary/5 p-5 space-y-4">
                    <header className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Briefcase className="h-3.5 w-3.5 text-primary" />
                        <span className="text-[10px] font-bold uppercase tracking-widest text-primary">
                          Gestión del Trámite
                        </span>
                      </div>
                      <span className="inline-flex items-center rounded-md border border-primary/20 bg-primary/10 px-2 py-0.5 text-[10px] font-bold text-primary">
                        {expediente.id_publico}
                      </span>
                    </header>

                    {/* Estado actual */}
                    <div className="text-center space-y-2">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-primary">
                        Estado Actual
                      </p>
                      <div className="inline-flex items-center justify-center gap-2 rounded-xl border-2 border-border bg-card px-5 py-2.5 min-w-[14rem]">
                        <Clock className="h-4 w-4 text-primary" />
                        <span className="text-sm font-bold uppercase tracking-wide text-foreground">
                          {estadoToken?.label ?? item.estado}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Actualizado{" "}
                        {formatDateTime(
                          item.fecha_inicio_gestion ??
                            expediente.fecha_registro,
                        )}
                      </p>
                    </div>

                    {/* Timeline */}
                    <div className="relative pl-7 space-y-3 border-t border-primary/20 pt-4">
                      <div
                        className="absolute left-[11px] top-7 bottom-7 w-0.5 bg-primary/30"
                        aria-hidden="true"
                      />
                      <div className="relative flex items-start gap-3">
                        <span className="absolute -left-7 top-1 h-2.5 w-2.5 shrink-0 rounded-full bg-primary ring-4 ring-primary/15" />
                        <div className="min-w-0">
                          <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                            Inicio del Trámite
                          </p>
                          <p className="font-mono text-xs font-semibold text-foreground">
                            {formatDateTime(expediente.fecha_registro)}
                          </p>
                        </div>
                      </div>
                      <div className="relative flex items-start gap-3">
                        <span
                          className={cn(
                            "absolute -left-7 top-1 h-2.5 w-2.5 shrink-0 rounded-full ring-4",
                            vencida
                              ? "bg-destructive ring-destructive/20"
                              : "bg-primary/40 ring-primary/10",
                          )}
                        />
                        <div className="min-w-0">
                          <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                            Fecha Límite
                          </p>
                          <p
                            className={cn(
                              "font-mono text-xs",
                              vencida
                                ? "font-bold text-destructive"
                                : "font-semibold text-foreground",
                            )}
                          >
                            {fechaLimite ? formatDateTime(fechaLimite) : "—"}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Equipo responsable */}
                    <div className="border-t border-primary/20 pt-4 space-y-2">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-primary">
                        Equipo Responsable
                      </p>
                      {item.areas_activas.length > 0 ? (
                        <ul className="space-y-2.5">
                          {item.areas_activas.map((area) => (
                            <li
                              key={area.area_id}
                              className="flex items-center gap-3"
                            >
                              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary font-black text-xs">
                                {area.area_nombre.charAt(0).toUpperCase()}
                              </div>
                              <div className="min-w-0 flex-1">
                                <p
                                  className="truncate text-sm font-semibold leading-tight text-foreground"
                                  title={area.area_nombre}
                                >
                                  {area.area_nombre}
                                </p>
                                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                                  {area.tipo_participacion === "PRINCIPAL"
                                    ? "Asignado Principal"
                                    : "Adjunto"}
                                </p>
                              </div>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-xs italic text-muted-foreground">
                          Sin equipo asignado
                        </p>
                      )}
                    </div>

                    {/* Bitácora link */}
                    <div className="border-t border-primary/20 pt-4 text-center">
                      <button
                        type="button"
                        className="text-xs font-semibold text-destructive hover:underline"
                        onClick={() => {
                          /* Bitácora page not part of quick-view scope */
                        }}
                      >
                        Ver bitácora completa →
                      </button>
                    </div>
                  </section>
                </div>
              </div>
            </div>
          </GenericModal.Body>

          {/* ── Footer — matches the form modal pattern (SolicitudFormModal:387-452) ── */}
          <GenericModal.Footer className="solicitud-modal-footer px-6 py-4 sm:px-8 bg-muted/30 border-t border-border">
            <div className="flex items-center justify-between gap-2 sm:gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground hidden sm:inline">
                  Vista de detalle rápido
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="default"
                  className={cn(BUTTON_PRESETS.modal.secondary, "gap-1.5")}
                  onClick={handlePrint}
                >
                  <Printer className="h-3.5 w-3.5" />
                  Imprimir
                </Button>
                <Button
                  variant="outline"
                  size="default"
                  className={BUTTON_PRESETS.modal.secondary}
                  onClick={() => onOpenChange(false)}
                >
                  Cerrar
                </Button>
                <Button
                  size="default"
                  className="h-10 rounded-xl font-bold gap-1.5 bg-foreground text-background hover:bg-black shadow-lg shadow-foreground/15"
                  onClick={handleVerDetalles}
                >
                  Ver Detalles Completos
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          </GenericModal.Footer>

          <GenericModal.CloseX />
        </GenericModal.Content>
      </GenericModal>

      <PrintPreviewModal
        open={printOpen}
        onOpenChange={setPrintOpen}
        title={`Solicitud ${expediente.id_publico}`}
        htmlContent={printHtml}
        previewContent={<SolicitudPrintPreview item={item} />}
      />
    </>
  );
}
