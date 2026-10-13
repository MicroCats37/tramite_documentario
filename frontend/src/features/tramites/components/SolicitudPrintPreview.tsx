/**
 * SolicitudPrintPreview — compact 1-page print preview.
 * Rendered inside PrintPreviewModal. Adapted for print: 1 page, no brand band,
 * no duplicate header (the SolicitudDetailModal's own header is hidden in
 * @media print), single-column section stack.
 */
"use client";

import {
  Briefcase,
  Calendar,
  FileText,
  Paperclip,
  Send,
  User,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  ESTADO_SOLICITUD,
  type EstadoSolicitud,
  PRIORIDAD_SOLICITUD,
  type PrioridadSolicitud,
  TIPO_PERSONA,
  type TipoPersona,
} from "@/shared/constants/tramite.tokens";
import type { SolicitudItem } from "../schemas/tramite.schema";

interface SolicitudPrintPreviewProps {
  item: SolicitudItem;
}

function SectionCard({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon?: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-border/80 bg-white">
      <div className="flex items-center gap-2 border-b border-primary/30 bg-muted/40 px-3 py-1.5">
        {Icon && (
          <Icon
            className="h-3.5 w-3.5 shrink-0 text-primary"
            aria-hidden="true"
          />
        )}
        <span className="text-[10px] font-black uppercase tracking-[0.16em] text-primary">
          {title}
        </span>
      </div>
      <div className="space-y-1.5 p-3">{children}</div>
    </div>
  );
}

function FieldRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string | number | null | undefined;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-2 leading-tight">
      <span className="shrink-0 text-[10px] font-semibold text-muted-foreground">
        {label}
      </span>
      <span
        className={`text-right text-xs font-bold text-foreground ${mono ? "font-mono" : ""}`}
        style={{ wordBreak: "break-word" }}
      >
        {value ?? "—"}
      </span>
    </div>
  );
}

function TwoUpRow({
  left,
  right,
}: {
  left: { label: string; value: string | number | null | undefined; mono?: boolean };
  right: { label: string; value: string | number | null | undefined; mono?: boolean };
}) {
  return (
    <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
      <FieldRow {...left} />
      <FieldRow {...right} />
    </div>
  );
}

/** Safe accessor for tipo_documento which may be a string or {id,nombre,descripcion} object. */
function getTipoDocumentoLabel(td: unknown): string {
  if (!td) return "—";
  if (typeof td === "object" && "nombre" in (td as object)) {
    return (td as { nombre: string }).nombre;
  }
  if (typeof td === "string") return td;
  return "—";
}

function formatDateShort(iso: string | null | undefined): string {
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

export function SolicitudPrintPreview({ item }: SolicitudPrintPreviewProps) {
  const estadoToken = ESTADO_SOLICITUD[item.estado as EstadoSolicitud];
  const prioridadToken =
    PRIORIDAD_SOLICITUD[item.prioridad as PrioridadSolicitud];
  const exp = item.expediente;
  const tipoPersonaToken = TIPO_PERSONA[exp.tipo_persona as TipoPersona];

  const nombreCompleto =
    exp.razon_social ||
    [exp.nombres, exp.apellidos].filter(Boolean).join(" ") ||
    "—";

  const docTipo = exp.dni ? "DNI" : exp.ruc ? "RUC" : exp.cip ? "CIP" : null;
  const docNumero = exp.dni || exp.ruc || exp.cip || "—";
  const identificacionLabel = docTipo ? `${docTipo} ${docNumero}` : docNumero;

  const areasPrincipales = item.areas_activas.filter(
    (a) => a.tipo_participacion === "PRINCIPAL",
  );
  const areasAdjuntas = item.areas_activas.filter(
    (a) => a.tipo_participacion === "ADJUNTA",
  );

  const fechaLimite = item.fecha_limite ? new Date(item.fecha_limite) : null;
  const vencida = fechaLimite
    ? fechaLimite < new Date() && item.estado !== "FINALIZADA"
    : false;

  const allAreas = [...areasPrincipales, ...areasAdjuntas];

  return (
    <div className="space-y-3 rounded-xl border border-border/60 bg-white p-4">
      {/* ── Compact header: icon + ID + type badge ── */}
      <div className="flex items-center gap-3 border-b border-border pb-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
          <FileText className="h-4 w-4 text-primary" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-base font-black tracking-tight text-foreground">
              {exp.id_publico}
            </span>
            <Badge
              variant="outline"
              className="text-[9px] font-bold uppercase tracking-wider"
            >
              Cédula Notificación
            </Badge>
          </div>
          <p className="mt-0.5 line-clamp-1 text-[11px] text-muted-foreground">
            <Calendar className="mr-1 inline h-3 w-3" />
            Registrado {formatDateTime(item.fecha_registro)}
          </p>
        </div>
      </div>

      {/* ── Single-column section stack (1 page) ── */}
      <div className="space-y-2.5">
        {/* Solicitante */}
        <SectionCard title="Solicitante" icon={User}>
          <FieldRow label="Razón social" value={nombreCompleto} />
          <TwoUpRow
            left={{ label: "Identificación", value: identificacionLabel, mono: true }}
            right={{ label: "Tipo persona", value: tipoPersonaToken.label }}
          />
          {(exp.telefono || exp.correo) && (
            <TwoUpRow
              left={{ label: "Teléfono", value: exp.telefono }}
              right={{ label: "Correo", value: exp.correo }}
            />
          )}
        </SectionCard>

        {/* Expediente */}
        <SectionCard title="Expediente" icon={FileText}>
          <FieldRow label="Asunto" value={exp.asunto} />
          <TwoUpRow
            left={{ label: "N.° documento", value: exp.numero_documento, mono: true }}
            right={{
              label: "Tipo documento",
              value: getTipoDocumentoLabel(exp.tipo_documento),
            }}
          />
          <TwoUpRow
            left={{ label: "Folios", value: exp.numero_folios }}
            right={{
              label: "Archivos",
              value: `${exp.archivos.length} adjunto${exp.archivos.length !== 1 ? "s" : ""}`,
            }}
          />
          <FieldRow label="Fecha registro" value={formatDateShort(exp.fecha_registro)} />
        </SectionCard>

        {/* Gestión del trámite — compact metadata + team */}
        <SectionCard title="Gestión del trámite" icon={Briefcase}>
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge className={estadoToken.badgeClass} variant="secondary">
              {estadoToken.label}
            </Badge>
            <Badge className={prioridadToken.badgeClass} variant="secondary">
              {prioridadToken.label}
            </Badge>
            <Badge className={tipoPersonaToken.badgeClass} variant="secondary">
              {tipoPersonaToken.label}
            </Badge>
          </div>
          <TwoUpRow
            left={{
              label: "Inicio gestión",
              value: formatDateTime(item.fecha_inicio_gestion),
            }}
            right={{
              label: "Fecha límite",
              value: formatDateShort(item.fecha_limite),
            }}
          />
          {vencida && (
            <p className="text-[10px] font-bold uppercase tracking-wider text-destructive">
              ⚠ Solicitud vencida
            </p>
          )}
          {allAreas.length > 0 && (
            <div className="border-t border-border/60 pt-1.5">
              <p className="mb-1 text-[9px] font-black uppercase tracking-wider text-muted-foreground">
                Derivado a
              </p>
              <div className="flex flex-wrap gap-1">
                {areasPrincipales.map((a) => (
                  <span
                    key={a.area_id}
                    className="rounded-md border border-primary/20 bg-primary/5 px-1.5 py-0.5 text-[10px] font-bold text-primary"
                  >
                    {a.area_nombre}
                  </span>
                ))}
                {areasAdjuntas.map((a) => (
                  <span
                    key={a.area_id}
                    className="rounded-md border border-border bg-muted/40 px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground"
                  >
                    {a.area_nombre} (Adj.)
                  </span>
                ))}
              </div>
            </div>
          )}
        </SectionCard>

        {/* Archivos adjuntos — minimal list, 1 line per file */}
        {exp.archivos.length > 0 && (
          <SectionCard title="Archivos adjuntos" icon={Paperclip}>
            <div className="space-y-0.5">
              {exp.archivos.map((archivo) => (
                <div
                  key={archivo.id}
                  className="flex items-center justify-between gap-2 text-[11px] leading-tight"
                >
                  <span className="truncate font-semibold text-foreground">
                    {archivo.nombre_original}
                  </span>
                  <span className="shrink-0 text-[9px] uppercase tracking-wider text-muted-foreground">
                    {archivo.tipo_archivo}
                  </span>
                </div>
              ))}
            </div>
          </SectionCard>
        )}

        {/* Footer with type-of-submission indicator */}
        <div className="flex items-center justify-between border-t border-border pt-2 text-[10px] text-muted-foreground">
          <span>
            <Send className="mr-1 inline h-3 w-3" />
            Documento oficial — Mesa de Partes CIP
          </span>
          <span>ID: {item.id.slice(0, 8)}</span>
        </div>
      </div>
    </div>
  );
}
