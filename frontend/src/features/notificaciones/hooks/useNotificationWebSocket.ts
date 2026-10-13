/**
 * useNotificationWebSocket — React hook for subscribing to the WebSocket manager.
 *
 * This hook does NOT create a WebSocket connection.
 * It subscribes to the singleton manager instance, which is shared across all
 * components. Multiple components can call this hook without creating multiple sockets.
 *
 * Usage:
 *   const { state, lastEvent } = useNotificationWebSocket();
 *
 * Or with full control:
 *   const { state, subscribe } = useNotificationWebSocket();
 *   subscribe((event) => { ... });
 *
 * The manager must be connected externally via notificationWsManager.connect().
 * Alternatively, pass connectOnMount: true to have this hook auto-connect.
 */

import { useEffect, useRef, useState } from "react";
import {
  type ConnectionState,
  type NotificationEvent,
  notificationWsManager,
} from "../services/notification-websocket.manager";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface UseNotificationWebSocketOptions {
  /**
   * If true, calls manager.connect() when the component mounts
   * and manager.disconnect() when it unmounts.
   * Default: false — caller is responsible for lifecycle.
   */
  connectOnMount?: boolean;
  /**
   * Optional WebSocket URL override.
   * Uses NEXT_PUBLIC_WS_URL / browser fallback if omitted.
   */
  url?: string;
}

export interface UseNotificationWebSocketReturn {
  /** Current connection state of the manager. */
  state: ConnectionState;
  /** The last notification event received, if any. */
  lastEvent: NotificationEvent | null;
  /** Subscribe to notification events. Returns an unsubscribe function. */
  subscribe: (handler: (event: NotificationEvent) => void) => () => void;
  /** Connect the WebSocket. Idempotent. */
  connect: (url?: string) => void;
  /** Intentionally disconnect the WebSocket. */
  disconnect: () => void;
}

// ── Hook ─────────────────────────────────────────────────────────────────────

/**
 * Subscribe to the NotificationWebSocketManager singleton.
 *
 * - Multiple components using this hook share the SAME underlying WebSocket.
 * - Does NOT automatically connect on mount unless `connectOnMount: true`.
 * - Returns the latest connection state and the last received event.
 */
export function useNotificationWebSocket(
  options: UseNotificationWebSocketOptions = {},
): UseNotificationWebSocketReturn {
  const { connectOnMount = false, url } = options;

  const [state, setState] = useState<ConnectionState>(
    notificationWsManager.state,
  );
  const [lastEvent, setLastEvent] = useState<NotificationEvent | null>(null);
  const lastEventRef = useRef<NotificationEvent | null>(null);

  // Subscribe to state changes
  useEffect(() => {
    const unsubscribe = notificationWsManager.onStateChange(setState);
    return unsubscribe;
  }, []);

  // Subscribe to events — store last event in state + ref
  useEffect(() => {
    const unsubscribe = notificationWsManager.subscribe((event) => {
      lastEventRef.current = event;
      setLastEvent(event);
    });
    return unsubscribe;
  }, []);

  // Auto-connect / disconnect lifecycle
  useEffect(() => {
    if (connectOnMount) {
      notificationWsManager.connect(url);
    }
    return () => {
      if (connectOnMount) {
        notificationWsManager.disconnect();
      }
    };
  }, [connectOnMount, url]);

  const connect = (connectUrl?: string) => {
    notificationWsManager.connect(connectUrl ?? url);
  };

  const disconnect = () => {
    notificationWsManager.disconnect();
  };

  const subscribe = (handler: (event: NotificationEvent) => void) => {
    return notificationWsManager.subscribe(handler);
  };

  return { state, lastEvent, subscribe, connect, disconnect };
}
