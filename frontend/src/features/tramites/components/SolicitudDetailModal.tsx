/**
 * SolicitudDetailModal — quick-view modal for Solicitud opened from the list.
 *
 * Layout (matches reference distribution):
 * - Header band: document icon, public id/title, badges (status/priority) on right
 * - Body: two-column responsive grid (balanced ~45/55 split)
 *   - Left: Solicitante card, then Expediente/Adjuntos card
 *   - Right: Gestión del trámite card with status panel, date timeline,
 *     responsible area/team
 * - Footer: Imprimir | Cerrar | Ver Detalles Completos (navegates to detail)
 *
 * Uses GenericModal compound pattern (aligns with app modal/form line).
 * Extra fields (fecha_cierre, observacion) show "—" — full detail fetch
 * is not needed for quick-view but Ver Detalles Completos links to detail page.
 */
"use client";

import { FileText, FolderOpen, Paperclip, Printer, User } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  ESTADO_SOLICITUD,
  type EstadoSolicitud,
  PRIORIDAD_SOLICITUD,
  type PrioridadSolicitud,
  TIPO_ARCHIVO,
  TIPO_PERSONA,
  type TipoArchivo,
  type TipoPersona,
} from "@/shared/constants/tramite.tokens";
import type { SolicitudItem } from "../schemas/tramite.schema";
import { PrintPreviewModal } from "./PrintPreviewModal";
import { buildSolicitudPrintHTML } from "./printExpediente";
import { getTipoDocumentoLabel } from "./SolicitudCard";
import { SolicitudPrintPreview } from "./SolicitudPrintPreview";

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

  // ── Derived data ─────────────────────────────────────────────────────────────
  const estadoToken = ESTADO_SOLICITUD[item.estado as EstadoSolicitud];
  const prioridadToken =
    PRIORIDAD_SOLICITUD[item.prioridad as PrioridadSolicitud];

  const nombreCompleto =
    expediente.razon_social ||
    [expediente.nombres, expediente.apellidos].filter(Boolean).join(" ") ||
    "—";

  // Areas principales
  const areasPrincipales = item.areas_activas.filter(
    (a) => a.tipo_participacion === "PRINCIPAL",
  );
  const areasAdjuntas = item.areas_activas.filter(
    (a) => a.tipo_participacion === "ADJUNTA",
  );

  // Registered time
  const registeredTime = formatDateTime(expediente.fecha_registro);

  // Tipos de archivo del expediente
  const archivos = expediente.archivos ?? [];

  // ── Print ──────────────────────────────────────────────────────────────────
  const handlePrint = () => {
    setPrintHtml(buildSolicitudPrintHTML(item));
    setPrintOpen(true);
  };

  // ── Ver Detalles Completos ─────────────────────────────────────────────────
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
          {/* ── Header — matches SolicitudFormModal pattern ─────────────────────── */}
          <GenericModal.Header className="bg-gradient-to-r from-primary/5 via-primary/[0.02] to-transparent border-b border-border px-6 py-5 sm:px-8">
            <div className="flex items-center gap-3 w-full">
              {/* Icon block — matches form modal pattern */}
              <div className="p-2.5 sm:p-3 bg-primary/10 rounded-xl sm:rounded-2xl border border-primary/20 shadow-sm shrink-0">
                <FileText className="h-5 w-5 text-primary" />
              </div>
              {/* Text block — eyebrow, title, subtitle (NO time, NO badges in header) */}
              <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                  {TIPO_PERSONA[expediente.tipo_persona as TipoPersona]
                    ?.label ?? expediente.tipo_persona}
                </span>
                <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground leading-tight">
                  {expediente.id_publico}
                </h2>
                <p className="hidden sm:block max-w-prose text-pretty line-clamp-2 text-sm text-muted-foreground leading-relaxed">
                  Solicitud #{item.id} · Registrado {registeredTime}
                </p>
              </div>
            </div>
          </GenericModal.Header>

          {/* ── Body ─────────────────────────────────────────────────────────── */}
          <GenericModal.Body className="flex-1 overflow-y-auto">
            <div className="solicitud-modal-body min-w-0 px-6 py-5">
              {/* Desktop: two columns; Mobile: stacked */}
              <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.95fr)] gap-5">
                {/* ── Left column ───────────────────────────────────────────── */}
                <div className="space-y-5">
                  {/* Solicitante card */}
                  <section className="solicitud-modal-card rounded-xl border border-border/50 bg-card p-4">
                    <p className="solicitud-modal-card-title text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
                      Solicitante
                    </p>
                    <div className="flex items-start gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted">
                        <User className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold leading-snug">
                          {nombreCompleto}
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {TIPO_PERSONA[expediente.tipo_persona as TipoPersona]
                            ?.label ?? expediente.tipo_persona}
                        </p>
                      </div>
                    </div>
                    {/* Contact info */}
                    {(expediente.correo || expediente.telefono) && (
                      <div className="mt-3 flex flex-col gap-1 border-t border-border pt-3">
                        {expediente.correo && (
                          <div className="flex flex-col gap-0.5">
                            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                              Correo
                            </span>
                            <span className="text-sm break-words">
                              {expediente.correo}
                            </span>
                          </div>
                        )}
                        {expediente.telefono && (
                          <div className="flex flex-col gap-0.5">
                            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                              Teléfono
                            </span>
                            <span className="text-sm">
                              {expediente.telefono}
                            </span>
                          </div>
                        )}
                      </div>
                    )}
                    {/* Identifiers */}
                    {(expediente.dni || expediente.ruc || expediente.cip) && (
                      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-3">
                        {expediente.dni && (
                          <div className="flex flex-col gap-0.5">
                            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                              DNI
                            </span>
                            <span className="text-sm font-mono">
                              {expediente.dni}
                            </span>
                          </div>
                        )}
                        {expediente.ruc && (
                          <div className="flex flex-col gap-0.5">
                            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                              RUC
                            </span>
                            <span className="text-sm font-mono">
                              {expediente.ruc}
                            </span>
                          </div>
                        )}
                        {expediente.cip && (
                          <div className="flex flex-col gap-0.5">
                            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                              CIP
                            </span>
                            <span className="text-sm font-mono">
                              {expediente.cip}
                            </span>
                          </div>
                        )}
                      </div>
                    )}
                  </section>

                  {/* Expediente card */}
                  <section className="solicitud-modal-card rounded-xl border border-border/50 bg-card p-4">
                    <p className="solicitud-modal-card-title text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
                      Expediente
                    </p>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Documento
                        </span>
                        <span className="text-sm font-medium">
                          {getTipoDocumentoLabel(expediente.tipo_documento)}
                          {expediente.numero_documento
                            ? ` ${expediente.numero_documento}`
                            : ""}
                        </span>
                      </div>
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Folios
                        </span>
                        <span className="text-sm font-medium">
                          {expediente.numero_folios}
                        </span>
                      </div>
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Fecha de Registro
                        </span>
                        <span className="text-sm font-medium">
                          {formatDate(expediente.fecha_registro)}
                        </span>
                      </div>
                      {typeof (expediente as { creado_por_nombres?: string })
                        .creado_por_nombres === "string" && (
                        <div className="flex flex-col gap-0.5">
                          <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                            Registrado por
                          </span>
                          <span className="text-sm font-medium">
                            {
                              (expediente as { creado_por_nombres?: string })
                                .creado_por_nombres
                            }
                          </span>
                        </div>
                      )}
                    </div>
                    {/* Asunto */}
                    {expediente.asunto && (
                      <div className="mt-3 border-t border-border pt-3">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Asunto
                        </span>
                        <p className="mt-1 text-sm leading-relaxed">
                          {expediente.asunto}
                        </p>
                      </div>
                    )}
                    {/* Observaciones */}
                    {expediente.observaciones && (
                      <div className="mt-3 border-t border-border pt-3">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Observaciones
                        </span>
                        <p className="mt-1 text-sm leading-relaxed">
                          {expediente.observaciones}
                        </p>
                      </div>
                    )}
                  </section>

                  {/* Archivos */}
                  {archivos.length > 0 && (
                    <section className="solicitud-modal-card rounded-xl border border-border/50 bg-card p-4">
                      <p className="solicitud-modal-card-title text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
                        Archivos ({archivos.length})
                      </p>
                      <div className="space-y-2">
                        {archivos.map((archivo) => (
                          <div
                            key={archivo.id}
                            className="flex items-center justify-between gap-3 rounded-lg border border-border bg-background px-3 py-2.5"
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <Paperclip className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                              <span className="truncate text-sm font-medium">
                                {archivo.nombre_original}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              <span
                                className={cn(
                                  "inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-medium",
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
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                className="h-7 w-7 print-hidden"
                                asChild
                              >
                                <a
                                  href={archivo.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  title="Abrir archivo"
                                >
                                  <FileText className="h-3.5 w-3.5" />
                                </a>
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </section>
                  )}
                </div>

                {/* ── Right column ─────────────────────────────────────────── */}
                <div className="space-y-5">
                  {/* Gestión del trámite card */}
                  <section className="solicitud-modal-card rounded-xl border border-border/50 bg-card p-4">
                    <p className="solicitud-modal-card-title text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
                      Gestión del Trámite
                    </p>

                    {/* Estado + Prioridad badges */}
                    {estadoToken ? (
                      <div className="mb-3 flex items-center gap-2 flex-wrap">
                        <span
                          className={cn(
                            "inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-semibold",
                            estadoToken.badgeClass,
                          )}
                        >
                          {estadoToken.label}
                        </span>
                        {prioridadToken && (
                          <span
                            className={cn(
                              "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium",
                              prioridadToken.badgeClass,
                            )}
                          >
                            {prioridadToken.label}
                          </span>
                        )}
                      </div>
                    ) : (
                      <p className="mb-3 text-sm text-muted-foreground">
                        Sin estado disponible
                      </p>
                    )}

                    {/* Dates grid */}
                    <div className="grid grid-cols-2 gap-3 border-t border-border pt-3">
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Fecha de Registro
                        </span>
                        <span className="text-sm font-medium">
                          {formatDate(expediente.fecha_registro)}
                        </span>
                      </div>
                      {item.fecha_inicio_gestion && (
                        <div className="flex flex-col gap-0.5">
                          <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                            Inicio de Gestión
                          </span>
                          <span className="text-sm font-medium">
                            {formatDate(item.fecha_inicio_gestion)}
                          </span>
                        </div>
                      )}
                      {item.fecha_limite && (
                        <div className="flex flex-col gap-0.5">
                          <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                            Fecha Límite
                          </span>
                          <span className="text-sm font-medium">
                            {formatDate(item.fecha_limite)}
                          </span>
                        </div>
                      )}
                      {/* fecha_cierre not available in SolicitudItem — shows "—" */}
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Fecha de Cierre
                        </span>
                        <span className="text-sm font-medium">—</span>
                      </div>
                    </div>

                    {/* Áreas activas */}
                    {areasPrincipales.length > 0 && (
                      <div className="mt-3 border-t border-border pt-3">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Área Principal
                        </span>
                        <div className="mt-1 flex flex-col gap-1">
                          {areasPrincipales.map((area) => (
                            <span
                              key={area.area_id}
                              className="inline-flex items-center gap-1.5 rounded-md border border-primary/20 bg-primary/5 px-2 py-1 text-xs font-bold text-primary w-fit"
                            >
                              <FolderOpen className="h-3 w-3" />
                              {area.area_nombre}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Áreas adjuntas */}
                    {areasAdjuntas.length > 0 && (
                      <div className="mt-3 border-t border-border pt-3">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Áreas Adjuntas
                        </span>
                        <div className="mt-1 flex flex-col gap-1">
                          {areasAdjuntas.map((area) => (
                            <span
                              key={area.area_id}
                              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-muted/40 px-2 py-1 text-xs font-semibold text-muted-foreground w-fit"
                            >
                              <FolderOpen className="h-3 w-3" />
                              {area.area_nombre}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Conteo pendiente */}
                    {(item.conteo_pendiente > 0 ||
                      item.conteo_en_gestion > 0) && (
                      <div className="mt-3 border-t border-border pt-3">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Resumen de Áreas
                        </span>
                        <div className="mt-1 flex flex-wrap gap-3">
                          {item.conteo_en_gestion > 0 && (
                            <div className="flex items-center gap-1.5">
                              <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                              <span className="text-xs font-medium">
                                {item.conteo_en_gestion} en gestión
                              </span>
                            </div>
                          )}
                          {item.conteo_pendiente > 0 && (
                            <div className="flex items-center gap-1.5">
                              <span className="h-2 w-2 rounded-full bg-amber-400" />
                              <span className="text-xs font-medium">
                                {item.conteo_pendiente} pendiente
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </section>
                </div>
              </div>
            </div>
          </GenericModal.Body>

          {/* ── Footer — matches SolicitudFormModal pattern ──────────────────────── */}
          <GenericModal.Footer className="bg-muted/30 border-t border-border px-6 py-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 print-hidden"
                onClick={handlePrint}
              >
                <Printer className="h-3.5 w-3.5" />
                Imprimir
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onOpenChange(false)}
              >
                Cerrar
              </Button>
              <Button
                variant="default"
                size="sm"
                className="gap-1.5"
                onClick={handleVerDetalles}
              >
                <FolderOpen className="h-3.5 w-3.5" />
                Ver Detalles Completos
              </Button>
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
