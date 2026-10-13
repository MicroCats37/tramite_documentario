/**
 * useNotificationRealtime — TanStack Query invalidation for notifications.
 *
 * Design contract (Apply 6 + post-fix):
 * - Uses useNotificationWebSocket (shared singleton manager — no duplicate sockets)
 * - On notification.created → refetch list + summary queries immediately
 * - On connected state → invalidate once to recover missed events
 * - On cleanup: cancels pending timers / unsubscribes
 * - NO polling, NO payload insert, NO optimistic cache, NO mass detail invalidation
 *
 * Stability contract:
 * - All callbacks use refs for `queryClient` to remain stable.
 * - No `queryClient` as dependency in any `useCallback` or `useEffect`.
 */

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import {
  NOTIFICACIONES_LIST_QUERY_KEY,
  NOTIFICACIONES_SUMMARY_KEY,
} from "./useNotificaciones";
import { useNotificationWebSocket } from "./useNotificationWebSocket";

// ── Hook ─────────────────────────────────────────────────────────────────────

/**
 * Subscribes to the notification WebSocket and refetches TanStack Query
 * notification queries when a new event arrives.
 *
 * - `notification.created` → refetch list + summary queries immediately
 * - Transition to `connected` → invalidate once to recover missed events
 *
 * Mount once per app session (e.g. in a top-level provider or layout shell).
 * The underlying WebSocket manager is a singleton — multiple subscribers share one socket.
 */
export function useNotificationRealtime(): void {
  const queryClient = useQueryClient();

  /** Track current queryClient in a ref to keep callbacks stable. */
  const queryClientRef = useRef(queryClient);
  queryClientRef.current = queryClient;

  /**
   * Flag: have we already invalidated on the current connected cycle?
   * Reset to false whenever the socket transitions away from connected.
   */
  const hasInvalidatedOnConnectRef = useRef(false);

  /** Whether the component is still mounted. */
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    console.debug("[WS-Notif] useNotificationRealtime mounted");
    return () => {
      mountedRef.current = false;
      console.debug("[WS-Notif] useNotificationRealtime unmounted");
    };
  }, []);

  /**
   * Refetch list + summary queries immediately.
   * Uses refs to keep this function stable (no React deps).
   *
   * Uses `refetchQueries` directly to force a fresh GET regardless of observer
   * state. Unlike invalidateQueries, refetchQueries triggers a real HTTP request
   * even when the query is currently active and fresh, ensuring the bell badge
   * updates the moment a notification arrives via WebSocket.
   */
  const refetchAll = (): void => {
    console.debug(
      "[WS-Notif] refetchAll: refetching list+summary queries",
    );
    const qc = queryClientRef.current;
    void qc.refetchQueries({
      queryKey: NOTIFICACIONES_LIST_QUERY_KEY,
      type: "active",
    });
    void qc.refetchQueries({
      queryKey: NOTIFICACIONES_SUMMARY_KEY,
      type: "active",
    });
    void qc.refetchQueries({
      queryKey: NOTIFICACIONES_LIST_QUERY_KEY,
      type: "inactive",
    });
    void qc.refetchQueries({
      queryKey: NOTIFICACIONES_SUMMARY_KEY,
      type: "inactive",
    });
  };

  // ── WebSocket subscription ─────────────────────────────────────────────────

  // connectOnMount: true — connects the singleton manager on provider mount,
  // disconnects on unmount. Multiple subscribers share the same socket.
  const { state, subscribe } = useNotificationWebSocket({
    connectOnMount: true,
  });

  useEffect(() => {
    // ── Connected → immediate one-shot invalidation (recover missed events) ──
    if (state === "connected") {
      if (!hasInvalidatedOnConnectRef.current && mountedRef.current) {
        hasInvalidatedOnConnectRef.current = true;
        refetchAll();
      }
    } else {
      // Reset so the next connection triggers a fresh invalidation
      hasInvalidatedOnConnectRef.current = false;
    }
  }, [state]);

  useEffect(() => {
    // ── notification.created → immediate refetch ──
    const unsubscribe = subscribe((event) => {
      console.debug(
        "[WS-Notif] useNotificationRealtime received event",
        event,
      );
      if (event.type === "notification.created") {
        if (!mountedRef.current) return;
        refetchAll();
      }
      // Unknown event types are silently ignored by the manager — nothing to do
    });

    return () => {
      unsubscribe();
    };
  }, [subscribe]);
}
