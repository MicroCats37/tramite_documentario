"use client";

import { useEffect, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Pill-style segmented tabs with a sliding wine-gradient active indicator.
 *
 * Mirrors the visual language of the login screen's tab control
 * (LoginClientShell.tsx:673-736): a `rounded-full` container with an
 * absolutely-positioned gradient pill that animates horizontally via
 * `translateX` when the active value changes. The active tab label is
 * painted in `text-primary-foreground` (white on wine).
 *
 * Use for top-level view selectors (e.g. "Todas / Mis áreas / ...").
 * For form-level switching inside a card, prefer the regular `<Tabs />`.
 */

export interface SegmentedTabOption<T extends string> {
  value: T;
  label: string;
  icon?: ReactNode;
}

export interface SegmentedTabsProps<T extends string> {
  value: T;
  onValueChange: (next: T) => void;
  options: ReadonlyArray<SegmentedTabOption<T>>;
  /** Optional accessible label for the group. */
  ariaLabel?: string;
  className?: string;
}

export function SegmentedTabs<T extends string>({
  value,
  onValueChange,
  options,
  ariaLabel,
  className,
}: SegmentedTabsProps<T>) {
  const total = options.length;
  const activeIndex = Math.max(
    0,
    options.findIndex((o) => o.value === value),
  );

  // Delay the slide animation until after the first paint so the indicator
  // doesn't animate from x=0 into position when the active value is not
  // the first option (e.g. when the URL already has `?vista=mias_areas`).
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        "relative flex items-center w-full bg-muted/40 p-1 rounded-full",
        "shadow-[inset_0_1px_2px_oklch(0_0_0_/_0.06)]",
        className,
      )}
    >
      {/* Sliding active indicator */}
      <div
        aria-hidden="true"
        className={cn(
          "absolute top-1 bottom-1 rounded-full",
          "bg-gradient-to-b from-[oklch(0.42_0.16_22)] to-[oklch(0.38_0.14_25)]",
          mounted
            ? "transition-all duration-300 ease-out"
            : "transition-none",
          "shadow-[0_2px_8px_oklch(0.42_0.16_22_/_0.3)]",
        )}
        style={{
          width: `calc(${100 / total}% - 4px)`,
          transform: `translateX(calc(${activeIndex} * 100% + ${activeIndex * 4}px))`,
        }}
      />

      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onValueChange(opt.value)}
            className={cn(
              "relative z-10 flex-1 flex items-center justify-center gap-2",
              "py-3 px-4 rounded-full",
              "transition-colors duration-200",
              active
                ? "text-primary-foreground font-bold"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {opt.icon ? (
              <span className="inline-flex shrink-0 items-center">
                {opt.icon}
              </span>
            ) : null}
            <span className="text-xs uppercase tracking-wider font-semibold whitespace-nowrap">
              {opt.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
