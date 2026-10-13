"use client";

import type { ReactNode } from "react";

/**
 * NotificationRealtimeBootstrap — mounts NotificationRealtimeProvider
 * inside the protected (authenticated) layout shell.
 *
 * This is a thin Client Component wrapper so the Server Component
 * protected layout can include the provider without needing "use client" on itself.
 *
 * Only one instance should exist in the protected layout tree.
 */

import { NotificationRealtimeProvider } from "@/features/notificaciones/providers/NotificationRealtimeProvider";

export function NotificationRealtimeBootstrap(): ReactNode {
  return <NotificationRealtimeProvider />;
}
