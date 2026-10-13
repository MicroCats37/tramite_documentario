"use client";

import { Printer } from "lucide-react";
import { useCallback } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";

/**
 * PrintPreviewModal — reusable modal for print previews of Expediente and Solicitud.
 * Uses GenericModal compound so the modal chrome (responsive size, scroll, close
 * behavior, preventCloseOnLoading) is consistent with every other modal in the app.
 *
 * On `Imprimir` click: builds a hidden iframe, injects the same token system
 * from the parent document so the print stylesheet resolves `var(--color-*)`
 * correctly, writes `htmlContent`, then triggers `iframe.print()`.
 */

const TOKEN_NAMES = [
  "--color-background",
  "--color-foreground",
  "--color-card",
  "--color-card-foreground",
  "--color-primary",
  "--color-primary-foreground",
  "--color-destructive",
  "--color-destructive-foreground",
  "--color-muted",
  "--color-muted-foreground",
  "--color-accent",
  "--color-accent-foreground",
  "--color-border",
  "--color-input",
  "--color-ring",
  "--color-secondary",
  "--color-secondary-foreground",
  "--color-popover",
  "--color-popover-foreground",
  "--color-success",
  "--color-success-foreground",
  "--color-warning",
  "--color-warning-foreground",
  "--radius",
  "--radius-sm",
  "--radius-md",
  "--radius-lg",
  "--radius-xl",
] as const;

function readParentTokens(): string {
  if (typeof window === "undefined") return "";
  const parentStyle = getComputedStyle(document.documentElement);
  return TOKEN_NAMES.map((name) => {
    const value = parentStyle.getPropertyValue(name).trim();
    return value ? `  ${name}: ${value};` : "";
  })
    .filter(Boolean)
    .join("\n");
}

interface PrintPreviewModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  /** HTML string used only for iframe/browser print output. */
  htmlContent: string;
  /** Optional React content rendered as the modal body preview. When provided, replaces dangerouslySetInnerHTML. */
  previewContent?: React.ReactNode;
}

export function PrintPreviewModal({
  open,
  onOpenChange,
  title,
  htmlContent,
  previewContent,
}: PrintPreviewModalProps) {
  const handlePrint = useCallback(() => {
    if (!htmlContent) return;

    const iframe = document.createElement("iframe");
    iframe.style.position = "fixed";
    iframe.style.right = "0";
    iframe.style.bottom = "0";
    iframe.style.width = "0";
    iframe.style.height = "0";
    iframe.style.border = "0";
    iframe.setAttribute("aria-hidden", "true");
    document.body.appendChild(iframe);

    const iframeDoc = iframe.contentWindow?.document;
    if (!iframeDoc) {
      document.body.removeChild(iframe);
      return;
    }

    const tokensBlock = readParentTokens();

    const styles = `
      :root {
${tokensBlock}
      }
      @page { margin: 18mm; }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        color: var(--color-foreground);
        font-family: Inter, "Plus Jakarta Sans", Arial, sans-serif;
        background: var(--color-card);
      }
      .sheet {
        min-height: 100vh;
        padding: 40px;
        border: 1px solid var(--color-border);
        border-radius: 28px;
        background:
          radial-gradient(circle at top right, color-mix(in oklch, var(--color-accent) 16%, transparent) 260px, transparent),
          linear-gradient(135deg, color-mix(in oklch, var(--color-primary) 8%, transparent), color-mix(in oklch, var(--color-card) 96%, transparent) 42%);
      }
      .brand {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
        padding-bottom: 22px;
        border-bottom: 2px solid var(--color-primary);
      }
      .brand-text { display: flex; flex-direction: column; }
      .brand-title {
        font-size: 13px;
        font-weight: 900;
        letter-spacing: .18em;
        color: var(--color-primary);
        text-transform: uppercase;
      }
      .brand-subtitle {
        margin-top: 4px;
        font-size: 11px;
        color: var(--color-muted-foreground);
        text-transform: uppercase;
        letter-spacing: .12em;
      }
      .seal {
        height: 72px;
        width: 72px;
        border-radius: 999px;
        background: var(--color-card);
        border: 2px solid var(--color-primary);
        display: grid;
        place-items: center;
        overflow: hidden;
        box-shadow: 0 4px 12px color-mix(in oklch, var(--color-primary) 18%, transparent);
      }
      .seal img { height: 60px; width: 60px; object-fit: contain; }
      h1 {
        margin: 30px 0 6px;
        font-size: 34px;
        line-height: 1;
        letter-spacing: -.04em;
        color: var(--color-foreground);
      }
      .public-id {
        color: var(--color-primary);
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-weight: 900;
      }
      .summary {
        margin: 18px 0 28px;
        max-width: 720px;
        color: var(--color-muted-foreground);
        font-size: 15px;
        line-height: 1.65;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px;
      }
      .field {
        padding: 14px 16px;
        border: 1px solid var(--color-border);
        border-radius: 18px;
        background: color-mix(in oklch, var(--color-card) 78%, transparent);
      }
      .label {
        color: var(--color-primary);
        font-size: 10px;
        font-weight: 900;
        letter-spacing: .16em;
        text-transform: uppercase;
      }
      .value {
        margin-top: 6px;
        font-size: 14px;
        font-weight: 700;
        color: var(--color-foreground);
      }
      .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
      .full { grid-column: 1 / -1; }
      .badges {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 18px 0 0;
      }
      .badge {
        border: 1px solid color-mix(in oklch, var(--color-primary) 28%, transparent);
        border-radius: 999px;
        padding: 6px 12px;
        color: var(--color-primary);
        background: color-mix(in oklch, var(--color-primary) 6%, transparent);
        font-size: 12px;
        font-weight: 800;
      }
      .areas-section { margin-top: 18px; }
      .areas-title {
        font-size: 10px;
        font-weight: 900;
        letter-spacing: .16em;
        text-transform: uppercase;
        color: var(--color-primary);
        margin-bottom: 10px;
      }
      .area-row { margin-bottom: 10px; }
      .area-row-label {
        font-size: 10px;
        font-weight: 800;
        letter-spacing: .14em;
        text-transform: uppercase;
        color: var(--color-muted-foreground);
        margin-bottom: 6px;
      }
      .area-badge {
        border: 1px solid color-mix(in oklch, var(--color-primary) 28%, transparent);
        border-radius: 999px;
        padding: 4px 12px;
        color: var(--color-primary);
        background: color-mix(in oklch, var(--color-primary) 6%, transparent);
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
        margin: 3px 4px 3px 0;
      }
      .area-section-badge {
        display: inline-block;
        border: 1px solid var(--color-border);
        border-radius: 999px;
        padding: 4px 12px;
        font-size: 11px;
        font-weight: 700;
        color: var(--color-muted-foreground);
        background: color-mix(in oklch, var(--color-muted) 60%, transparent);
        margin: 3px 4px 3px 0;
      }
      .footer {
        margin-top: 34px;
        padding-top: 18px;
        border-top: 1px solid var(--color-border);
        color: var(--color-muted-foreground);
        font-size: 11px;
        display: flex;
        justify-content: space-between;
      }
      @media print {
        html, body { margin: 0; padding: 0; }
        .sheet { border: 0; padding: 0; border-radius: 0; }
      }
    `;

    iframeDoc.open();
    iframeDoc.write(
      `<!doctype html><html lang="es"><head><meta charset="utf-8" /><title>${title.replace(/[<>]/g, "")}</title><style>${styles}</style></head><body>${htmlContent}</body></html>`,
    );
    iframeDoc.close();

    iframe.contentWindow?.focus();
    iframe.contentWindow?.print();

    const cleanup = () => {
      if (document.body.contains(iframe)) {
        document.body.removeChild(iframe);
      }
    };
    iframe.contentWindow?.addEventListener("afterprint", cleanup, {
      once: true,
    });
    setTimeout(cleanup, 5000);
  }, [htmlContent, title]);

  return (
    <GenericModal open={open} onOpenChange={onOpenChange}>
      <GenericModal.Content size="full">
        {/* Header — matches the form modal pattern (SolicitudFormModal:242-260) */}
        <div className="bg-gradient-to-r from-primary/5 via-primary/[0.02] to-transparent border-b border-border px-6 py-5 sm:px-8">
          <div className="flex items-center gap-3 w-full">
            <div className="p-2 sm:p-2.5 bg-primary/10 rounded-xl sm:rounded-2xl border border-primary/20 shadow-sm shrink-0">
              <Printer className="h-5 w-5 text-primary" />
            </div>
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                Mesa de Partes
              </span>
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground leading-tight">
                {title}
              </h2>
              <p className="hidden sm:block max-w-prose text-pretty line-clamp-2 text-sm text-muted-foreground leading-relaxed">
                Vista previa del documento antes de imprimir. Verifica los datos
                y archivos adjuntos.
              </p>
            </div>
          </div>
        </div>

        <GenericModal.Body scrollable className="bg-muted/20 p-5">
          {previewContent ? (
            previewContent
          ) : (
            <div
              className="[&_.sheet]:!min-h-auto [&_.sheet]:!border [&_.sheet]:!rounded-2xl [&_.sheet]:!shadow-sm"
              // biome-ignore lint/security/noDangerouslySetInnerHtml: htmlContent is produced by buildSolicitudPrintHTML/buildExpedientePrintHTML, both internal builders that only emit controlled HTML (no user input).
              dangerouslySetInnerHTML={{ __html: htmlContent }}
            />
          )}
        </GenericModal.Body>

        {/* Footer — matches the form modal pattern (SolicitudFormModal:387-452) */}
        <GenericModal.Footer className="px-6 py-4 sm:px-8 bg-muted/30 border-t border-border">
          <div className="flex items-center justify-between gap-2 sm:gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground hidden sm:inline">
                Documento listo para impresión
              </span>
            </div>
            <div className="flex items-center gap-2">
              <GenericModal.Close asChild>
                <Button type="button" variant="outline">
                  Cerrar
                </Button>
              </GenericModal.Close>
              <Button type="button" variant="default" onClick={handlePrint}>
                <Printer className="size-4" />
                Imprimir
              </Button>
            </div>
          </div>
        </GenericModal.Footer>

        <GenericModal.CloseX />
      </GenericModal.Content>
    </GenericModal>
  );
}
