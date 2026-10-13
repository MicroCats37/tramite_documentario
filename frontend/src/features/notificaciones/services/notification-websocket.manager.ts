/**
 * NotificationWebSocketManager — singleton WebSocket connection manager.
 *
 * Single connection per browser tab, shared by all subscribers.
 * Manages lifecycle, reconnection with exponential backoff, and event dispatch.
 *
 * Design principles (Apply 5 contract):
 * - NO Socket.IO — native WebSocket only
 * - NO token in URL / subprotocol / localStorage
 * - Cookie auth sent automatically by the browser on handshake
 * - Idempotent connect() — no duplicate sockets
 * - Multiple subscribers share one socket
 * - Exponential backoff with jitter, max 30s
 * - Pauses reconnect when navigator.onLine === false
 * - 4401/4403 close codes = do NOT auto-reconnect
 * - No polling, no heartbeat, no JWT storage
 */

// ── Types ─────────────────────────────────────────────────────────────────────────

export type WsReadyState = 0 | 1 | 2 | 3; // CONNECTING | OPEN | CLOSING | CLOSED

export type NotificationEvent = {
  type: "notification.created";
  notification_id: string;
  occurred_at: string;
  version: 1;
};

export type ConnectionState =
  | "idle"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected";

export type ConnectionStateChangeHandler = (state: ConnectionState) => void;
export type NotificationEventHandler = (event: NotificationEvent) => void;

/** Factory type for creating WebSocket instances — allows test injection. */
export type WebSocketFactory = (url: string) => WebSocketLike;

export interface WebSocketLike {
  readonly readyState: WsReadyState;
  url: string;
  onopen: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent) => void) | null;
  onclose: ((event: CloseEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  close(code?: number, reason?: string): void;
}

// ── Constants ───────────────────────────────────────────────────────────────────

const CLOSE_CODE_AUTH = 4401 as const;
const CLOSE_CODE_GOING_AWAY = 4403 as const;
const MAX_RECONNECT_DELAY_MS = 30_000;
const INITIAL_RECONNECT_DELAY_MS = 1_000;
const JITTER_FACTOR = 0.3;

// ── Manager ─────────────────────────────────────────────────────────────────────

class NotificationWebSocketManager {
  private static _instance: NotificationWebSocketManager | null = null;

  private _socket: WebSocketLike | null = null;
  private _state: ConnectionState = "idle";
  private _subscribers: Set<NotificationEventHandler> = new Set();
  private _stateSubscribers: Set<ConnectionStateChangeHandler> = new Set();
  private _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _reconnectAttempt = 0;
  private _intentionalClose = false;
  private _url: string | null = null;
  private readonly _wsFactory: WebSocketFactory;

  private constructor(wsFactory?: WebSocketFactory) {
    this._wsFactory = wsFactory ?? this._defaultWsFactory();
    // Listen for online/offline to pause/resume reconnection
    if (typeof window !== "undefined") {
      window.addEventListener("online", this._handleOnline);
      window.addEventListener("offline", this._handleOffline);
    }
  }

  private _defaultWsFactory(): WebSocketFactory {
    return (url: string) => new WebSocket(url) as WebSocketLike;
  }

  static get instance(): NotificationWebSocketManager {
    if (!NotificationWebSocketManager._instance) {
      NotificationWebSocketManager._instance =
        new NotificationWebSocketManager();
    }
    return NotificationWebSocketManager._instance;
  }

  /**
   * Create a manager instance with an injectable WebSocket factory — for testing only.
   * Resets the singleton so the next `.instance` call returns a fresh manager.
   */
  static createWithFactory(
    factory: WebSocketFactory,
  ): NotificationWebSocketManager {
    NotificationWebSocketManager._instance = null;
    const manager = new NotificationWebSocketManager(factory);
    NotificationWebSocketManager._instance = manager;
    return manager;
  }

  // ── Public API ───────────────────────────────────────────────────────────────

  /**
   * Current connection state.
   */
  get state(): ConnectionState {
    return this._state;
  }

  /**
   * Returns the URL used for the current connection, or null if idle.
   */
  get url(): string | null {
    return this._url;
  }

  /**
   * Connect (or reconnect) the WebSocket.
   * Idempotent: if CONNECTING or OPEN, this is a no-op.
   * Resets reconnect state and schedules connect.
   */
  connect(url?: string): void {
    const wsUrl = url ?? this._resolveUrl();
    this._url = wsUrl;
    this._intentionalClose = false;

    const readyState = this._socket?.readyState as WsReadyState | undefined;
    if (readyState === 0 /* CONNECTING */ || readyState === 1 /* OPEN */) {
      return; // Already connected or connecting — idempotent
    }

    this._clearReconnectTimer();
    this._setState("connecting");
    this._createSocket(wsUrl);
    console.debug("[WS-Notif] opening", wsUrl);
  }

  /**
   * Intentionally close the WebSocket.
   * Sets intentionalClose flag so reconnect is skipped.
   */
  disconnect(): void {
    this._intentionalClose = true;
    this._clearReconnectTimer();
    this._closeSocket();
    this._setState("disconnected");
  }

  /**
   * Subscribe to notification events.
   * Returns an unsubscribe function.
   */
  subscribe(handler: NotificationEventHandler): () => void {
    this._subscribers.add(handler);
    return () => {
      this._subscribers.delete(handler);
    };
  }

  /**
   * Subscribe to connection state changes.
   * Returns an unsubscribe function.
   */
  onStateChange(handler: ConnectionStateChangeHandler): () => void {
    this._stateSubscribers.add(handler);
    // Immediately emit current state
    handler(this._state);
    return () => {
      this._stateSubscribers.delete(handler);
    };
  }

  /**
   * Reset all state — for testing only.
   */
  _resetForTesting(): void {
    this._intentionalClose = false;
    this._reconnectAttempt = 0;
    this._clearReconnectTimer();
    if (this._socket) {
      this._socket.onopen = null;
      this._socket.onmessage = null;
      this._socket.onclose = null;
      this._socket.onerror = null;
      try {
        this._socket.close();
      } catch {
        // Ignore
      }
      this._socket = null;
    }
    this._setState("idle");
  }

  // ── Private ─────────────────────────────────────────────────────────────────

  private _resolveUrl(): string {
    // 1. Explicit env var wins (works for both browser and server).
    if (typeof process !== "undefined" && process.env.NEXT_PUBLIC_WS_URL) {
      return process.env.NEXT_PUBLIC_WS_URL;
    }
    // 2. Browser: derive ws/wss from current location (proxy-friendly).
    if (typeof window !== "undefined") {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host;
      return `${protocol}//${host}/ws/notificaciones/`;
    }
    // 3. Server-side: derive from BACKEND_HOST (no hardcode).
    //    Required because Next.js may need the WS endpoint during SSR
    //    or in test environments without a window object.
    const backendHost = process.env.BACKEND_HOST;
    if (!backendHost) {
      throw new Error(
        "Cannot resolve WS URL server-side: set NEXT_PUBLIC_WS_URL or BACKEND_HOST env var.",
      );
    }
    return `ws://${backendHost}/ws/notificaciones/`;
  }

  private _createSocket(url: string): void {
    // Close any existing socket before creating a new one
    if (this._socket) {
      this._socket.onopen = null;
      this._socket.onmessage = null;
      this._socket.onclose = null;
      this._socket.onerror = null;
      try {
        this._socket.close();
      } catch {
        // Ignore errors during close
      }
      this._socket = null;
    }

    const socket = this._wsFactory(url);

    socket.onopen = this._handleOpen;
    socket.onmessage = this._handleMessage;
    socket.onclose = this._handleClose;
    socket.onerror = this._handleError;

    this._socket = socket;
  }

  private _closeSocket(): void {
    if (this._socket) {
      this._socket.onopen = null;
      this._socket.onmessage = null;
      this._socket.onclose = null;
      this._socket.onerror = null;
      try {
        this._socket.close();
      } catch {
        // Ignore
      }
      this._socket = null;
    }
  }

  private _handleOpen = (): void => {
    this._reconnectAttempt = 0;
    this._setState("connected");
  };

  private _handleMessage = (event: MessageEvent): void => {
    const raw = event.data;
    const preview =
      typeof raw === "string"
        ? raw.length > 80
          ? raw.slice(0, 80) + "…"
          : raw
        : String(raw);
    console.debug(`[WS-Notif] recv raw len=${typeof raw === "string" ? raw.length : "?"} preview=${preview}`);
    const parsed = this._parseEvent(raw);
    if (parsed === null) {
      console.debug("[WS-Notif] drop: parse returned null");
      return; // Invalid message — ignore silently
    }
    console.debug("[WS-Notif] parse OK", parsed);
    for (const handler of this._subscribers) {
      try {
        handler(parsed);
      } catch {
        // Subscriber error must not break the manager
      }
    }
  };

  private _handleClose = (event: CloseEvent): void => {
    const code = event.code as number;

    // Auth failure (4401) or going away (4403) — do NOT reconnect automatically
    if (code === CLOSE_CODE_AUTH || code === CLOSE_CODE_GOING_AWAY) {
      this._setState("disconnected");
      this._intentionalClose = true;
      return;
    }

    // Intentional close — no reconnect
    if (this._intentionalClose) {
      this._setState("disconnected");
      return;
    }

    // Abnormal close — schedule reconnect with backoff
    this._scheduleReconnect();
  };

  private _handleError = (): void => {
    // WebSocket error events don't have useful detail.
    // The close event following an error will handle reconnection logic.
  };

  private _handleOnline = (): void => {
    if (this._state === "disconnected" && !this._intentionalClose) {
      this._scheduleReconnect();
    }
  };

  private _handleOffline = (): void => {
    // Pause reconnection — wait for online event
    this._clearReconnectTimer();
    if (this._state === "reconnecting" || this._state === "connecting") {
      this._setState("disconnected");
    }
  };

  private _scheduleReconnect(): void {
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      this._setState("disconnected");
      return;
    }
    if (this._intentionalClose) {
      return;
    }

    this._clearReconnectTimer();
    this._setState("reconnecting");

    const delay = this._computeBackoffDelay();
    this._reconnectTimer = setTimeout(() => {
      if (this._url) {
        this.connect(this._url);
      }
    }, delay);
  }

  private _computeBackoffDelay(): number {
    // Exponential backoff: 1s, 2s, 4s, 8s, ... capped at 30s
    const exponential = Math.min(
      INITIAL_RECONNECT_DELAY_MS * 2 ** this._reconnectAttempt,
      MAX_RECONNECT_DELAY_MS,
    );
    // Add jitter: ±30% to prevent thundering herd
    const jitter = exponential * JITTER_FACTOR * (Math.random() * 2 - 1);
    this._reconnectAttempt += 1;
    return Math.round(Math.max(0, exponential + jitter));
  }

  private _clearReconnectTimer(): void {
    if (this._reconnectTimer !== null) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
  }

  private _setState(state: ConnectionState): void {
    if (this._state === state) {
      return;
    }
    const prev = this._state;
    this._state = state;
    console.debug(`[WS-Notif] state ${prev} → ${state}`);
    for (const handler of this._stateSubscribers) {
      try {
        handler(state);
      } catch {
        // Subscriber error must not break the manager
      }
    }
  }

  /**
   * Parse and validate an incoming WebSocket message.
   * Returns a valid NotificationEvent or null if invalid/unexpected.
   * Silently ignores messages that don't match the expected schema.
   */
  private _parseEvent(raw: string): NotificationEvent | null {
    let data: unknown;
    try {
      data = JSON.parse(raw);
    } catch {
      console.debug("[WS-Notif] drop: not valid JSON");
      return null; // Not valid JSON — ignore
    }

    if (typeof data !== "object" || data === null || Array.isArray(data)) {
      console.debug("[WS-Notif] drop: not a plain object");
      return null;
    }

    const obj = data as Record<string, unknown>;

    if (obj.type === "notification.created") {
      return this._parseNotificationCreated(obj);
    }

    console.debug(`[WS-Notif] drop: unknown type "${obj.type}"`);
    return null; // Unknown event type — ignore
  }

  private _parseNotificationCreated(
    obj: Record<string, unknown>,
  ): NotificationEvent | null {
    if (obj.version !== 1) {
      console.debug(`[WS-Notif] drop: version ${obj.version} !== 1`);
      return null;
    }
    if (
      typeof obj.notification_id !== "string" ||
      obj.notification_id.length === 0
    ) {
      console.debug("[WS-Notif] drop: empty/invalid notification_id");
      return null;
    }
    if (typeof obj.occurred_at !== "string" || obj.occurred_at.length === 0) {
      console.debug("[WS-Notif] drop: empty occurred_at");
      return null;
    }
    // Basic ISO8601 parseability check — Date.parse handles ISO8601
    const parsed = Date.parse(obj.occurred_at);
    if (Number.isNaN(parsed)) {
      console.debug(`[WS-Notif] drop: invalid ISO8601 "${obj.occurred_at}"`);
      return null;
    }
    return {
      type: "notification.created",
      notification_id: obj.notification_id as string,
      occurred_at: obj.occurred_at as string,
      version: 1,
    };
  }
}

// ── Exports ─────────────────────────────────────────────────────────────────────

export const notificationWsManager = NotificationWebSocketManager.instance;
export { NotificationWebSocketManager };
