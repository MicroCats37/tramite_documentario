/**
 * Button preset tokens — semantic className bundles for the Solicitud flow.
 *
 * Why this exists: the audit (sdd/explore/solicitud-frontend-ux-audit) found
 * inconsistent button styling across modals and inline actions. This file is
 * the single source of truth for which classes belong together.
 *
 * Conventions:
 * - All colors/radius reference CSS variables defined in `app/globals.css`
 *   via the standard Tailwind v4 utility names (bg-primary, rounded-xl, etc.).
 *   Do NOT hardcode hex/oklch values here.
 * - `modal.*`    — footer of any modal (h-10 = comfortable touch target)
 * - `inline.*`   — buttons inside cards/sections (h-8 = compact but tappable)
 * - `compact.*`  — badges, dense lists, icon-adjacent (h-7 = small)
 * - `destructive` variant always pairs with variant="destructive" on the Button
 * - Spinner uses lucide-react's `Loader2` icon with `SPINNER_CLASS`
 *
 * How to use:
 *   import { BUTTON_PRESETS, SPINNER_CLASS } from "@/shared/constants/button.tokens";
 *
 *   <Button variant="destructive" className={BUTTON_PRESETS.modal.destructive}>
 *     {isLoading && <Loader2 className={SPINNER_CLASS} />}
 *     Confirmar
 *   </Button>
 */

export const BUTTON_PRESETS = {
  modal: {
    primary: "h-10 rounded-xl font-bold gap-1.5",
    secondary: "h-10 rounded-xl font-semibold",
    destructive: "h-10 rounded-xl font-bold gap-1.5",
  },
  inline: {
    primary: "h-8 rounded-lg font-semibold gap-1.5",
    secondary: "h-8 rounded-lg font-semibold gap-1.5",
    destructive: "h-8 rounded-lg font-semibold gap-1.5",
  },
  compact: {
    primary: "h-7 rounded-lg font-semibold gap-1",
    secondary: "h-7 rounded-lg font-semibold gap-1",
    destructive: "h-7 rounded-lg font-semibold gap-1",
  },
} as const;

export const SPINNER_CLASS = "h-4 w-4 animate-spin";

export type ButtonPreset = (typeof BUTTON_PRESETS)[keyof typeof BUTTON_PRESETS];
