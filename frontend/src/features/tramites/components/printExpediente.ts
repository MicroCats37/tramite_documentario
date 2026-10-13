/**
 * printExpediente — independent print HTML for Solicitud/Expediente documents.
 *
 * The print/PDF is a SELF-CONTAINED document. Its HTML uses INLINE STYLES
 * (no external <style> block) so the print always renders correctly in the
 * browser's print dialog — regardless of iframe vs page print, browser quirks,
 * or CSS scoping issues.
 *
 * Print pipeline (matches the established pattern in features/liquidaciones/pdf):
 * 1. createPdfFrame() — isolated iframe off-screen
 * 2. write HTML with absolute image URLs (window.location.origin + path)
 * 3. await waitForImages() — guarantees the logo (and any future <img>) is
 *    fully loaded BEFORE calling window.print(). Without this the print dialog
 *    can render before the image request completes and the logo comes out
 *    blank.
 * 4. frameWindow.print()
 *
 * Color palette (literal values, mirrors the app's brand):
 * - Wine primary: #8f1027
 * - Ink:           #1a1a1a
 * - Muted:         #6b6b6b
 * - Card:          #ffffff
 * - Border:        #e5e5e5
 * - Soft tinted:   rgba(143, 16, 39, 0.05)
 */

import { createPdfFrame, waitForImages } from "@/components-app/pdf/pdfShell";
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
import type { ExpedienteItem, SolicitudItem } from "../schemas/tramite.schema";

const WINE = "#8f1027";
const INK = "#1a1a1a";
const MUTED = "#6b6b6b";
const CARD = "#ffffff";
const BORDER = "#e5e5e5";
const TINTED = "rgba(143, 16, 39, 0.06)";

function escapeHtml(value: unknown): string {
  return String(value ?? "—")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("es-PE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function getTipoDocumentoLabel(td: unknown): string {
  if (!td) return "—";
  if (typeof td === "object" && "nombre" in (td as object)) {
    return (td as { nombre: string }).nombre;
  }
  if (typeof td === "string") return td;
  return "—";
}

function personaLabel(exp: ExpedienteItem): string {
  if (exp.razon_social) return exp.razon_social;
  return [exp.nombres, exp.apellidos].filter(Boolean).join(" ") || "—";
}

function identityWithPrefix(exp: ExpedienteItem): string {
  if (exp.dni) return `DNI ${exp.dni}`;
  if (exp.ruc) return `RUC ${exp.ruc}`;
  if (exp.cip) return `CIP ${exp.cip}`;
  return "—";
}

/* ── Inline-styled HTML primitives ────────────────────────────────────────── */

function fieldRow(label: string, value: string | number, mono = false): string {
  return `<div style="display:flex;align-items:baseline;justify-content:space-between;gap:8px;padding:2px 0;">
    <span style="color:${MUTED};font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;flex-shrink:0;">${escapeHtml(label)}</span>
    <span style="font-size:9.5px;font-weight:700;color:${INK};text-align:right;word-break:break-word;${mono ? "font-family:ui-monospace,SFMono-Regular,Menlo,monospace;" : ""}">${escapeHtml(value)}</span>
  </div>`;
}

function fieldRowPair(
  left: string,
  leftValue: string | number,
  right: string,
  rightValue: string | number,
): string {
  return `<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:2px 0;">
    <div style="display:flex;align-items:baseline;justify-content:space-between;gap:6px;">
      <span style="color:${MUTED};font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;flex-shrink:0;">${escapeHtml(left)}</span>
      <span style="font-size:9.5px;font-weight:700;color:${INK};text-align:right;word-break:break-word;">${escapeHtml(leftValue)}</span>
    </div>
    <div style="display:flex;align-items:baseline;justify-content:space-between;gap:6px;">
      <span style="color:${MUTED};font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;flex-shrink:0;">${escapeHtml(right)}</span>
      <span style="font-size:9.5px;font-weight:700;color:${INK};text-align:right;word-break:break-word;">${escapeHtml(rightValue)}</span>
    </div>
  </div>`;
}

function block(title: string, content: string): string {
  return `<div style="margin-bottom:5px;padding:7px 9px;border:0.5px solid ${BORDER};border-left:3px solid ${WINE};border-radius:5px;background:${CARD};">
    <div style="font-size:8px;font-weight:800;text-transform:uppercase;letter-spacing:.12em;color:${WINE};margin-bottom:4px;padding-bottom:3px;border-bottom:0.5px dashed ${BORDER};">${escapeHtml(title)}</div>
    ${content}
  </div>`;
}

function badge(label: string, kind: "wine" | "neutral" = "wine"): string {
  const bg = kind === "wine" ? WINE : "#f0f0f0";
  const fg = kind === "wine" ? CARD : INK;
  return `<span style="display:inline-block;font-size:8px;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:${fg};background:${bg};border-radius:4px;padding:2px 7px;">${escapeHtml(label)}</span>`;
}

function badgeRow(
  items: { label: string; kind?: "wine" | "neutral" }[],
): string {
  if (!items.length) return "";
  return `<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px;">${items.map((i) => badge(i.label, i.kind)).join("")}</div>`;
}

function logoBlock(): string {
  return `<div style="display:flex;align-items:center;gap:12px;padding:6px 0 10px 0;border-bottom:1.5px solid ${WINE};margin-bottom:10px;">
    <div style="width:54px;height:54px;border-radius:50%;background:${CARD};border:2px solid ${WINE};display:grid;place-items:center;overflow:hidden;flex-shrink:0;box-sizing:border-box;">
      <img src="/images/logo.png" alt="CIP" style="width:46px;height:46px;object-fit:contain;display:block;" onerror="this.style.display='none'" />
    </div>
    <div style="flex:1;min-width:0;">
      <div style="font-size:7.5px;font-weight:900;text-transform:uppercase;letter-spacing:.18em;color:${WINE};line-height:1;">Colegio de Ingenieros del Perú</div>
      <div style="font-size:7px;font-weight:700;text-transform:uppercase;letter-spacing:.14em;color:${MUTED};margin-top:2px;line-height:1;">Mesa de Partes · Trámite Documentario</div>
    </div>
  </div>`;
}

function header(idPublico: string, tipoLabel: string): string {
  return `<div style="display:flex;align-items:center;gap:10px;padding:6px 0 8px 0;border-bottom:1px solid ${BORDER};margin-bottom:8px;">
    <span style="font-size:15px;font-weight:800;color:${INK};font-family:ui-monospace,SFMono-Regular,Menlo,monospace;line-height:1;">${escapeHtml(idPublico)}</span>
    <span style="font-size:8px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:${WINE};border:1px solid ${WINE};border-radius:999px;padding:2px 8px;margin-left:auto;">${escapeHtml(tipoLabel)}</span>
  </div>`;
}

function footer(): string {
  return `<div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;padding-top:5px;border-top:0.5px solid ${BORDER};color:${MUTED};font-size:7.5px;letter-spacing:.04em;">
    <span>Mesa de Partes — Colegio de Ingenieros del Perú</span>
    <span>${formatDate(new Date().toISOString())}</span>
  </div>`;
}

function archivoRow(archivo: {
  nombre_original: string;
  tipo_archivo: string;
}): string {
  const tipoLabel =
    TIPO_ARCHIVO[archivo.tipo_archivo as TipoArchivo]?.label ??
    archivo.tipo_archivo;
  const isPrincipal = archivo.tipo_archivo === "PRINCIPAL";
  return `<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;padding:3px 0;border-bottom:0.5px dashed ${BORDER};">
    <span style="font-size:9.5px;font-weight:600;color:${INK};overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(archivo.nombre_original)}</span>
    <span style="flex-shrink:0;font-size:7.5px;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:${isPrincipal ? WINE : MUTED};background:${isPrincipal ? TINTED : "#f0f0f0"};border:0.5px solid ${isPrincipal ? WINE : BORDER};border-radius:3px;padding:1px 5px;">${escapeHtml(tipoLabel)}</span>
  </div>`;
}

/* ── HTML builders ─────────────────────────────────────────────────────────── */

export function buildExpedientePrintHTML(expediente: ExpedienteItem): string {
  const tipoPersonaLabel =
    TIPO_PERSONA[expediente.tipo_persona as TipoPersona]?.label ??
    expediente.tipo_persona;

  return `<main style="padding:0;max-width:100%;color:${INK};font-family:Inter,&quot;Plus Jakarta Sans&quot;,Arial,sans-serif;font-size:10px;line-height:1.35;background:${CARD};">
    ${logoBlock()}
    ${header(expediente.id_publico, "Cédula de Notificación")}
    ${block(
      "Solicitante",
      fieldRow("Persona o entidad", personaLabel(expediente)) +
        fieldRowPair(
          "Tipo",
          tipoPersonaLabel,
          "Identificación",
          identityWithPrefix(expediente),
        ) +
        (expediente.telefono || expediente.correo
          ? fieldRowPair(
              "Teléfono",
              expediente.telefono || "—",
              "Correo",
              expediente.correo || "—",
            )
          : ""),
    )}
    ${block(
      "Expediente",
      fieldRow("Asunto", expediente.asunto) +
        fieldRowPair(
          "N.° documento",
          expediente.numero_documento || "—",
          "Tipo documento",
          getTipoDocumentoLabel(expediente.tipo_documento),
        ) +
        fieldRowPair(
          "Folios",
          String(expediente.numero_folios),
          "N.° registro",
          expediente.numero || "—",
        ) +
        fieldRow("Fecha registro", formatDate(expediente.fecha_registro)) +
        (expediente.observaciones
          ? `<div style="margin-top:4px;padding-top:4px;border-top:0.5px dashed ${BORDER};">
              <div style="color:${MUTED};font-size:7.5px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:2px;">Observaciones</div>
              <div style="font-size:9.5px;color:${INK};white-space:pre-wrap;line-height:1.4;">${escapeHtml(expediente.observaciones)}</div>
            </div>`
          : ""),
    )}
    ${
      expediente.archivos.length > 0
        ? block(
            `Archivos adjuntos (${expediente.archivos.length})`,
            expediente.archivos.map(archivoRow).join(""),
          )
        : ""
    }
    ${footer()}
  </main>`;
}

export function buildSolicitudPrintHTML(solicitud: SolicitudItem): string {
  const exp = solicitud.expediente;
  const estadoLabel =
    ESTADO_SOLICITUD[solicitud.estado as EstadoSolicitud]?.label ??
    solicitud.estado;
  const prioridadLabel =
    PRIORIDAD_SOLICITUD[solicitud.prioridad as PrioridadSolicitud]?.label ??
    solicitud.prioridad;
  const tipoPersonaLabel =
    TIPO_PERSONA[exp.tipo_persona as TipoPersona]?.label ?? exp.tipo_persona;

  const areasPrincipales = solicitud.areas_activas.filter(
    (a) => a.tipo_participacion === "PRINCIPAL",
  );
  const areasAdjuntas = solicitud.areas_activas.filter(
    (a) => a.tipo_participacion === "ADJUNTA",
  );
  const allAreas = [...areasPrincipales, ...areasAdjuntas];

  const areasChips = allAreas.length
    ? allAreas
        .map(
          (a) =>
            `<span style="display:inline-block;font-size:9px;font-weight:700;padding:1px 6px;border-radius:3px;margin:2px 3px 2px 0;${a.tipo_participacion === "PRINCIPAL" ? `color:${WINE};background:${TINTED};border:0.5px solid ${WINE};` : `color:${MUTED};background:#f0f0f0;border:0.5px solid ${BORDER};`}">${escapeHtml(a.area_nombre)}</span>`,
        )
        .join("")
    : `<span style="color:${MUTED};font-style:italic;">Sin derivación</span>`;

  const fechaLimiteStr = formatDate(solicitud.fecha_limite);
  const fechaLimiteVencida =
    solicitud.fecha_limite &&
    new Date(solicitud.fecha_limite) < new Date() &&
    solicitud.estado !== "FINALIZADA";

  return `<main style="padding:0;max-width:100%;color:${INK};font-family:Inter,&quot;Plus Jakarta Sans&quot;,Arial,sans-serif;font-size:10px;line-height:1.35;background:${CARD};">
    ${logoBlock()}
    ${header(exp.id_publico, "Cédula de Notificación")}
    ${badgeRow([
      { label: estadoLabel, kind: "wine" },
      { label: prioridadLabel, kind: "wine" },
      { label: tipoPersonaLabel, kind: "wine" },
    ])}
    ${block(
      "Solicitante",
      fieldRow("Persona o entidad", personaLabel(exp)) +
        fieldRowPair(
          "Tipo",
          tipoPersonaLabel,
          "Identificación",
          identityWithPrefix(exp),
        ) +
        (exp.telefono || exp.correo
          ? fieldRowPair(
              "Teléfono",
              exp.telefono || "—",
              "Correo",
              exp.correo || "—",
            )
          : ""),
    )}
    ${block(
      "Expediente",
      fieldRow("Asunto", exp.asunto) +
        fieldRowPair(
          "N.° documento",
          exp.numero_documento || "—",
          "Tipo documento",
          getTipoDocumentoLabel(exp.tipo_documento),
        ) +
        fieldRowPair(
          "Folios",
          String(exp.numero_folios),
          "N.° registro",
          exp.numero || "—",
        ) +
        fieldRowPair(
          "Registro",
          formatDate(solicitud.fecha_registro),
          "Límite",
          fechaLimiteStr,
        ) +
        (fechaLimiteVencida
          ? `<div style="margin-top:4px;padding:3px 6px;background:rgba(204, 51, 51, 0.1);border:0.5px solid #cc3333;border-radius:3px;color:#cc3333;font-size:8.5px;font-weight:800;text-transform:uppercase;letter-spacing:.1em;">⚠ Solicitud vencida</div>`
          : "") +
        (exp.observaciones
          ? `<div style="margin-top:5px;padding-top:5px;border-top:0.5px dashed ${BORDER};">
              <div style="color:${MUTED};font-size:7.5px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:2px;">Observaciones</div>
              <div style="font-size:9.5px;color:${INK};white-space:pre-wrap;line-height:1.4;">${escapeHtml(exp.observaciones)}</div>
            </div>`
          : ""),
    )}
    ${block(
      "Derivado a",
      `<div style="line-height:1.6;">${areasChips}</div>` +
        (solicitud.conteo_pendiente > 0 || solicitud.conteo_en_gestion > 0
          ? `<div style="margin-top:5px;padding-top:5px;border-top:0.5px dashed ${BORDER};display:flex;gap:8px;font-size:8.5px;color:${MUTED};">
              ${
                solicitud.conteo_pendiente > 0
                  ? `<span>● Pendientes: <strong style="color:${INK};">${solicitud.conteo_pendiente}</strong></span>`
                  : ""
              }
              ${
                solicitud.conteo_en_gestion > 0
                  ? `<span>● En gestión: <strong style="color:${INK};">${solicitud.conteo_en_gestion}</strong></span>`
                  : ""
              }
            </div>`
          : ""),
    )}
    ${
      exp.archivos.length > 0
        ? block(
            `Archivos adjuntos (${exp.archivos.length})`,
            exp.archivos.map(archivoRow).join(""),
          )
        : ""
    }
    ${footer()}
  </main>`;
}

/**
 * Convert a relative image src (e.g. "/images/logo.png") to an inline base64
 * data URI by fetching it in the parent document and encoding via FileReader.
 * Required because the print iframe is on `about:blank` after document.write
 * and cannot load cross-origin resources — even same-origin localhost images
 * are blocked when the iframe's effective origin is null.
 *
 * The data URI travels with the HTML so the <img> renders immediately inside
 * the print iframe, no network request needed.
 */
async function inlineImagesAsDataUri(html: string): Promise<string> {
  if (typeof window === "undefined") return html;
  // Find all relative image paths in the HTML
  const matches = [...html.matchAll(/src="(\/[^"]+)"/g)];
  if (matches.length === 0) return html;

  let result = html;
  // Dedupe paths
  const uniquePaths = [...new Set(matches.map((m) => m[1]))];
  for (const path of uniquePaths) {
    try {
      const res = await fetch(path, { cache: "force-cache" });
      if (!res.ok) continue;
      const blob = await res.blob();
      const dataUri = await new Promise<string | null>((resolve) => {
        const reader = new FileReader();
        reader.onload = () =>
          resolve(typeof reader.result === "string" ? reader.result : null);
        reader.onerror = () => resolve(null);
        reader.readAsDataURL(blob);
      });
      if (dataUri) {
        result = result.replaceAll(`src="${path}"`, `src="${dataUri}"`);
      }
    } catch {
      // If the image can't be fetched, keep the original path — the print
      // may still work in some browsers.
    }
  }
  return result;
}

/**
 * Opens the print dialog with the given HTML content using the established
 * app pattern (features/liquidaciones/pdf/printLiquidacion.ts):
 * 1. Convert any <img> references to inline base64 data URIs (so the iframe,
 *    which ends up on about:blank, doesn't need to fetch cross-origin)
 * 2. Create an off-screen iframe via createPdfFrame
 * 3. Write the HTML
 * 4. await waitForImages() — should be instant since images are inline
 * 5. frameWindow.print()
 * 6. Remove the iframe after a short delay
 *
 * The HTML is self-contained (inline styles only) so no <style> block is needed.
 */
export async function printWithWindow(
  htmlContent: string,
  title: string,
): Promise<void> {
  const finalHtml = await inlineImagesAsDataUri(htmlContent);

  const { frame, frameWindow, frameDocument } = createPdfFrame({
    width: "920px",
    height: "1123px",
  });

  try {
    const cb = Date.now();
    frameDocument.open();
    frameDocument.write(
      `<!doctype html><html lang="es"><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
<style>
  @page { size: A4; margin: 10mm; }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 0; background: #ffffff; }
  ::-webkit-scrollbar { display: none; }
</style>
</head><body>${finalHtml}<!-- cb=${cb} --></body></html>`,
    );
    frameDocument.close();

    // Images are now inline data URIs, but waitForImages still gives the
    // browser a chance to decode/render them before the print dialog opens.
    await waitForImages(frameDocument.body);

    frameWindow.focus();
    frameWindow.print();

    setTimeout(() => frame.remove(), 1000);
  } catch (err) {
    frame.remove();
    throw err;
  }
}
