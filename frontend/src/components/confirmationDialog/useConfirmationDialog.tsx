"use client";

import { type ComponentType, useCallback, useState } from "react";
import { ConfirmationDialog } from "./ConfirmationDialog";

export interface ConfirmOptions {
  title: string;
  description?: React.ReactNode;
  consequences?: string[];
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "default" | "destructive";
  icon?: ComponentType<{ className?: string }>;
  /**
   * Sync or async handler executed when the user confirms.
   * If it throws or rejects, the modal stays open and the returned Promise
   * resolves to `false`. On success, the modal closes and resolves to `true`.
   */
  onConfirm?: () => void | Promise<void>;
}

/**
 * Imperative confirmation dialog with async-aware loading state.
 *
 * @example
 * ```tsx
 * const { confirm, Dialog } = useConfirmationDialog();
 *
 * const ok = await confirm({
 *   title: "Finalizar solicitud",
 *   description: "Esta acción cerrará todos los períodos abiertos.",
 *   consequences: [
 *     "Los períodos activos se cerrarán en cascada",
 *     "Otro usuario deberá reasignarse para continuar",
 *   ],
 *   variant: "destructive",
 *   icon: AlertTriangle,
 *   onConfirm: () => finalizarMutation.mutateAsync(),
 * });
 * if (ok) {
 *   // do something on success
 * }
 * return Dialog;
 * ```
 */
export function useConfirmationDialog() {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const [resolveRef, setResolveRef] = useState<
    ((value: boolean) => void) | null
  >(null);
  const [isConfirming, setIsConfirming] = useState(false);

  const confirm = useCallback((opts: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setOptions(opts);
      setResolveRef(() => resolve);
      setOpen(true);
    });
  }, []);

  const handleConfirm = useCallback(async () => {
    if (!options) return;

    if (!options.onConfirm) {
      resolveRef?.(true);
      setOpen(false);
      setOptions(null);
      return;
    }

    setIsConfirming(true);
    try {
      await options.onConfirm();
      resolveRef?.(true);
      setOpen(false);
      setOptions(null);
    } catch {
      // Keep the modal open so the caller can show an error.
      // The Promise stays pending — caller should not rely on it for errors.
    } finally {
      setIsConfirming(false);
    }
  }, [options, resolveRef]);

  const handleOpenChange = useCallback(
    (next: boolean) => {
      if (next) {
        setOpen(true);
        return;
      }
      // While confirming, block any close attempt (backdrop, ESC, X).
      if (isConfirming) return;
      resolveRef?.(false);
      setOpen(false);
      setOptions(null);
    },
    [isConfirming, resolveRef],
  );

  const Dialog = options ? (
    <ConfirmationDialog
      open={open}
      onOpenChange={handleOpenChange}
      title={options.title}
      description={options.description}
      consequences={options.consequences}
      confirmLabel={options.confirmLabel}
      cancelLabel={options.cancelLabel}
      variant={options.variant}
      icon={options.icon}
      isLoading={isConfirming}
      onConfirm={handleConfirm}
    />
  ) : null;

  return { confirm, Dialog, isConfirming };
}
