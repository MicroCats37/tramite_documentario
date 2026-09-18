/**
 * ExpedienteDetailModal — shows full Expediente detail inside a GenericModal.
 *
 * Used from Solicitud detail to display expediente data without navigating away.
 * Receives the expediente data directly from the parent (already fetched via
 * useSolicitudDetail) to avoid an extra round-trip.
 *
 * Converted to GenericModal compound pattern (aligns with app modal/form line).
 * Redesigned with:
 * - Strong header with expediente ID, badges, and registered time
 * - Two-column responsive layout (stacked on mobile)
 * - Left: Solicitante + Expediente + Archivos cards
 * - Right: Gestión del trámite card
 * - Footer with Imprimir + Cerrar actions
 * - Print-optimized CSS
 */
"use client";

import { FileText, FolderOpen, Paperclip, Printer, User } from "lucide-react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import type {
  ExpedienteDetail,
  SolicitudDetail,
} from "@/features/tramites/schemas/tramite.schema";
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
import { getTipoDocumentoLabel } from "./SolicitudCard";

interface ExpedienteDetailModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  expediente: ExpedienteDetail | null | undefined;
  /** Optional full SolicitudDetail for Gestión del trámite card fields. */
  solicitud?: Partial<SolicitudDetail> | null | undefined;
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

export function ExpedienteDetailModal({
  open,
  onOpenChange,
  expediente,
  solicitud,
}: ExpedienteDetailModalProps) {
  const handlePrint = () => window.print();

  if (!expediente) return null;

  const nombreCompleto =
    expediente.razon_social ||
    `${expediente.nombres ?? ""} ${expediente.apellidos ?? ""}`.trim() ||
    "—";

  // ── Gestión del trámite derived data ─────────────────────────────────────────
  const estadoToken = solicitud?.estado
    ? ESTADO_SOLICITUD[solicitud.estado as EstadoSolicitud]
    : null;
  const prioridadToken = solicitud?.prioridad
    ? PRIORIDAD_SOLICITUD[solicitud.prioridad as PrioridadSolicitud]
    : null;

  // Principal area: first area with tipo_participacion PRINCIPAL from asignaciones
  const principalArea = solicitud?.asignaciones?.find(
    (a) => a.periodos?.[0]?.tipo_participacion === "PRINCIPAL",
  );
  const principalAreaNombre = principalArea?.area_nombre ?? null;

  // Registered time — formatted datetime
  const registeredTime = formatDateTime(expediente.fecha_registro);

  return (
    <GenericModal open={open} onOpenChange={onOpenChange}>
      <GenericModal.Content
        size="xl"
        className="expediente-modal-shell w-[min(900px,calc(100vw-2rem))] max-w-[min(900px,calc(100vw-2rem))]"
      >
        {/* ── Header — matches SolicitudFormModal pattern ────────────────────────── */}
        <GenericModal.Header className="bg-gradient-to-r from-primary/5 via-primary/[0.02] to-transparent border-b border-border px-6 py-5 sm:px-8">
          <div className="flex items-center gap-3 w-full">
            {/* Icon block — matches form modal pattern */}
            <div className="p-2.5 sm:p-3 bg-primary/10 rounded-xl sm:rounded-2xl border border-primary/20 shadow-sm shrink-0">
              <FolderOpen className="h-5 w-5 text-primary" />
            </div>
            {/* Text block — eyebrow, title, subtitle (NO time, NO badges in header) */}
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                {TIPO_PERSONA[expediente.tipo_persona as TipoPersona]?.label ??
                  expediente.tipo_persona}
              </span>
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground leading-tight">
                {expediente.id_publico ?? "Expediente"}
              </h2>
              <p className="hidden sm:block max-w-prose text-pretty line-clamp-2 text-sm text-muted-foreground leading-relaxed">
                Expediente · Registrado {registeredTime}
              </p>
            </div>
          </div>
        </GenericModal.Header>

        {/* ── Body: two-column layout ────────────────────────────────────────── */}
        <GenericModal.Body className="flex-1 overflow-y-auto">
          <div className="expediente-modal-body min-w-0 px-6 py-5">
            {/* Desktop: two columns; Mobile: stacked (grid-template-columns: 1fr) */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {/* ── Left column ─────────────────────────────────────────────── */}
              <div className="space-y-5">
                {/* Solicitante card */}
                <section className="expediente-card rounded-xl border border-border/50 bg-card p-4">
                  <p className="expediente-card-title text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
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
                          <span className="text-sm">{expediente.telefono}</span>
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
                </section>

                {/* Expediente card */}
                <section className="expediente-card rounded-xl border border-border/50 bg-card p-4">
                  <p className="expediente-card-title text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
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
                    {expediente.creado_por_nombres && (
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Registrado por
                        </span>
                        <span className="text-sm font-medium">
                          {expediente.creado_por_nombres}
                        </span>
                      </div>
                    )}
                  </div>
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
                {expediente.archivos && expediente.archivos.length > 0 && (
                  <section className="expediente-card rounded-xl border border-border/50 bg-card p-4">
                    <p className="expediente-card-title text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
                      Archivos ({expediente.archivos.length})
                    </p>
                    <div className="space-y-2">
                      {expediente.archivos.map((archivo) => (
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
                              {TIPO_ARCHIVO[archivo.tipo_archivo as TipoArchivo]
                                ?.label ?? archivo.tipo_archivo}
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

              {/* ── Right column ─────────────────────────────────────────────── */}
              <div className="space-y-5">
                {/* Gestión del trámite card */}
                <section className="expediente-card rounded-xl border border-border/50 bg-card p-4">
                  <p className="expediente-card-title text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
                    Gestión del Trámite
                  </p>

                  {/* Estado */}
                  {estadoToken ? (
                    <div className="mb-3 flex items-center gap-2">
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
                    {solicitud?.fecha_inicio_gestion && (
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Inicio de Gestión
                        </span>
                        <span className="text-sm font-medium">
                          {formatDate(solicitud.fecha_inicio_gestion)}
                        </span>
                      </div>
                    )}
                    {solicitud?.fecha_limite && (
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Fecha Límite
                        </span>
                        <span className="text-sm font-medium">
                          {formatDate(solicitud.fecha_limite)}
                        </span>
                      </div>
                    )}
                    {solicitud?.fecha_cierre && (
                      <div className="flex flex-col gap-0.5">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Fecha de Cierre
                        </span>
                        <span className="text-sm font-medium">
                          {formatDate(solicitud.fecha_cierre)}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Principal area */}
                  {principalAreaNombre && (
                    <div className="mt-3 border-t border-border pt-3">
                      <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                        Área Principal
                      </span>
                      <p className="mt-1 text-sm font-medium">
                        {principalAreaNombre}
                      </p>
                    </div>
                  )}

                  {/* Team / participantes from principal area */}
                  {solicitud?.asignaciones &&
                    solicitud.asignaciones.length > 0 && (
                      <div className="mt-3 border-t border-border pt-3">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          Equipo
                        </span>
                        <div className="mt-1 flex flex-col gap-1">
                          {solicitud.asignaciones.flatMap((asignacion) =>
                            (asignacion.participantes ?? [])
                              .filter((p) => p.activo)
                              .map((participante) => (
                                <span
                                  key={participante.usuario_id}
                                  className="text-sm"
                                >
                                  {participante.usuario_nombres}
                                  {participante.rol && (
                                    <span className="ml-1.5 text-xs text-muted-foreground">
                                      · {participante.rol}
                                    </span>
                                  )}
                                </span>
                              )),
                          )}
                          {solicitud.asignaciones.flatMap((asignacion) =>
                            (asignacion.participantes ?? []).filter(
                              (p) => p.activo,
                            ),
                          ).length === 0 && (
                            <span className="text-sm text-muted-foreground">
                              Sin participantes activos
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                </section>

                {/* Antecedentes */}
                {expediente.antecedentes &&
                  expediente.antecedentes.length > 0 && (
                    <section className="expediente-card rounded-xl border border-border/50 bg-card p-4">
                      <p className="expediente-card-title text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
                        Antecedentes ({expediente.antecedentes.length})
                      </p>
                      <div className="space-y-2">
                        {expediente.antecedentes.map((ant) => (
                          <div
                            key={ant.id_publico}
                            className="rounded-lg border border-border bg-background px-3 py-2"
                          >
                            <span className="text-sm font-mono font-medium">
                              {ant.id_publico}
                            </span>
                            {ant.categoria && (
                              <p className="text-xs text-muted-foreground mt-0.5">
                                {ant.categoria}
                              </p>
                            )}
                            {ant.observaciones && (
                              <p className="mt-1 text-xs text-muted-foreground italic">
                                {ant.observaciones}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </section>
                  )}
              </div>
            </div>
          </div>
        </GenericModal.Body>

        {/* ── Footer — matches SolicitudFormModal pattern ────────────────────────────────── */}
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
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
          >
            Cerrar
          </Button>
        </GenericModal.Footer>

        <GenericModal.CloseX />
      </GenericModal.Content>
    </GenericModal>
  );
}
