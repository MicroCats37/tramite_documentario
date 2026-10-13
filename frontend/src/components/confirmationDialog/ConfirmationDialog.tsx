"use client";

import { Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  BUTTON_PRESETS,
  SPINNER_CLASS,
} from "@/shared/constants/button.tokens";

export type ConfirmationDialogVariant = "default" | "destructive";

export interface ConfirmationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  /** Intro text or any rich content shown under the title. */
  description?: ReactNode;
  /**
   * Bulleted list of consequences shown below the description.
   * Use this to make irreversible or multi-actor actions explicit
   * (e.g. "El área dejará de participar", "Otro usuario deberá hacerse cargo").
   */
  consequences?: string[];
  /**
   * Optional icon shown to the left of the title.
   * Recommended: AlertTriangle / Trash2 for destructive, Info for default.
   */
  icon?: React.ComponentType<{ className?: string }>;
  confirmLabel?: string;
  cancelLabel?: string;
  /** "destructive" maps to the destructive button variant. */
  variant?: ConfirmationDialogVariant;
  /**
   * When true, the confirm button shows a spinner and both buttons are disabled.
   * Combined with preventCloseOnLoading (default true) it also blocks ESC/backdrop/X.
   */
  isLoading?: boolean;
  /**
   * Default true. While isLoading, prevent ESC/backdrop/X from closing the modal.
   */
  preventCloseOnLoading?: boolean;
  /**
   * Sync or async handler. The component does NOT auto-close on success — the
   * caller is responsible for calling onOpenChange(false) (or letting the
   * surrounding state decide). The async path is awaited before resolving.
   */
  onConfirm: () => void | Promise<void>;
}

export function ConfirmationDialog({
  open,
  onOpenChange,
  title,
  description,
  consequences,
  icon: Icon,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  variant = "default",
  isLoading = false,
  preventCloseOnLoading = true,
  onConfirm,
}: ConfirmationDialogProps) {
  const isDestructive = variant === "destructive";
  const shouldBlockClose = isLoading && preventCloseOnLoading;

  const handleConfirm = async () => {
    if (isLoading) return;
    try {
      await onConfirm();
    } catch {
      // Caller is responsible for surfacing the error; we keep the modal open
      // implicitly because the caller did not call onOpenChange(false).
    }
  };

  return (
    <GenericModal
      open={open}
      onOpenChange={onOpenChange}
      preventClose={shouldBlockClose}
    >
      <GenericModal.Content>
        {/* ── Header — matches the form modal pattern (SolicitudFormModal:242-260) ── */}
        <div className="bg-gradient-to-r from-primary/5 via-primary/[0.02] to-transparent border-b border-border px-6 py-5 sm:px-8">
          <div className="flex items-center gap-3 w-full">
            {Icon && (
              <div
                className={cn(
                  "p-2 sm:p-2.5 rounded-xl sm:rounded-2xl border shadow-sm shrink-0",
                  isDestructive
                    ? "bg-destructive/10 border-destructive/30"
                    : "bg-primary/10 border-primary/20",
                )}
                aria-hidden="true"
              >
                <Icon
                  className={cn(
                    "h-5 w-5",
                    isDestructive ? "text-destructive" : "text-primary",
                  )}
                />
              </div>
            )}
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                Confirmación
              </span>
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground leading-tight">
                {title}
              </h2>
              {description && (
                <p className="hidden sm:block max-w-prose text-pretty line-clamp-2 text-sm text-muted-foreground leading-relaxed">
                  {description}
                </p>
              )}
            </div>
          </div>
        </div>

        <GenericModal.Body scrollable={false} className="px-6 py-5 space-y-4">
          {description && (
            <p className="text-sm text-muted-foreground leading-relaxed">
              {description}
            </p>
          )}

          {consequences && consequences.length > 0 && (
            <div
              className={cn(
                "rounded-lg border px-4 py-3",
                isDestructive
                  ? "border-destructive/30 bg-destructive/5"
                  : "border-border bg-muted/30",
              )}
            >
              <p
                className={cn(
                  "text-[10px] font-bold uppercase tracking-widest mb-2",
                  isDestructive ? "text-destructive" : "text-muted-foreground",
                )}
              >
                Qué va a pasar
              </p>
              <ul className="space-y-1.5 text-sm text-foreground">
                {consequences.map((c, i) => (
                  <li key={`${i}-${c}`} className="flex items-start gap-2">
                    <span
                      className={cn(
                        "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                        isDestructive ? "bg-destructive" : "bg-primary",
                      )}
                      aria-hidden="true"
                    />
                    <span className="leading-snug">{c}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </GenericModal.Body>

        <GenericModal.Footer className="px-6 py-4 sm:px-8 bg-muted/30 border-t border-border">
          <div className="flex items-center justify-between gap-2 sm:gap-3">
            <div className="flex items-center gap-2" />
            <div className="flex items-center gap-2">
              <GenericModal.Close asChild>
                <Button
                  type="button"
                  variant="outline"
                  disabled={isLoading}
                  className={BUTTON_PRESETS.modal.secondary}
                >
                  {cancelLabel}
                </Button>
              </GenericModal.Close>
              <Button
                type="button"
                onClick={handleConfirm}
                disabled={isLoading}
                className={
                  isDestructive
                    ? BUTTON_PRESETS.modal.destructive
                    : BUTTON_PRESETS.modal.primary
                }
              >
                {isLoading && <Loader2 className={SPINNER_CLASS} />}
                {confirmLabel}
              </Button>
            </div>
          </div>
        </GenericModal.Footer>
      </GenericModal.Content>
    </GenericModal>
  );
}
