"use client";

/**
 * NotificationRealtimeProvider — mounts the WebSocket → TanStack Query
 * invalidation integration once per app session.
 *
 * Mount this once in an auth-guarded layout or shell (e.g. the protected layout).
 * This component renders nothing; it only wires up the realtime invalidation hook.
 *
 * Design contract (Apply 6):
 * - Singleton: only one instance should exist in the tree
 * - Uses the shared WebSocket manager via useNotificationWebSocket
 * - No duplicate sockets — manager is shared across all subscribers
 */

import { useNotificationRealtime } from "../hooks/useNotificationRealtime";

/**
 * Provider component that activates notification realtime invalidation.
 * Render once at the authenticated app shell level.
 *
 * Does not render any UI.
 */
export function NotificationRealtimeProvider(): null {
  useNotificationRealtime();
  return null;
}
