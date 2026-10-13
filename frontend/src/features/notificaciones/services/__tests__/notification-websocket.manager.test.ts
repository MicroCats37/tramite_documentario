/**
 * Unit tests for NotificationWebSocketManager.
 *
 * Uses node:test + node:assert/strict (built into Node 18+).
 * No external test framework needed.
 *
 * NOTE: node:test runs in Node.js, which lacks DOM APIs (CloseEvent, MessageEvent).
 * The DOM shims below provide minimal equivalents for testing only.
 * Production code runs in the browser where these APIs exist natively.
 */

// ── DOM shims for Node.js test environment ───────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const _globalThis = globalThis as typeof globalThis & Record<string, unknown>;

if (!_globalThis.CloseEvent) {
  // biome-ignore lint/suspicious/noExplicitAny: Node.js DOM shim — intentional
  (_globalThis as any).CloseEvent = class CloseEvent extends Event {
    readonly code: number;
    readonly reason: string;
    readonly wasClean: boolean;
    // biome-ignore lint/suspicious/noExplicitAny: Node.js DOM shim — intentional
    constructor(type: string, init?: any) {
      super(type);
      this.code = init?.code ?? 0;
      this.reason = init?.reason ?? "";
      this.wasClean = init?.wasClean ?? false;
    }
  };
}

if (!_globalThis.MessageEvent) {
  // biome-ignore lint/suspicious/noExplicitAny: Node.js DOM shim — intentional
  (_globalThis as any).MessageEvent = class MessageEvent extends Event {
    readonly data: unknown;
    // biome-ignore lint/suspicious/noExplicitAny: Node.js DOM shim — intentional
    constructor(type: string, init?: any) {
      super(type);
      this.data = init?.data ?? null;
    }
  };
}

/**
 * Unit tests for NotificationWebSocketManager.
 *
 * Uses node:test + node:assert/strict (built into Node 18+).
 * No external test framework needed.
 *
 * Tests cover:
 * 1. connect idempotence
 * 2. two subscribers share one socket
 * 3. intentional disconnect does not reconnect
 * 4. abnormal close transitions to reconnecting
 * 5. 4401 / 4403 close codes do NOT reconnect
 * 6. offline pauses reconnect
 * 7. valid event distributed; invalid/ignored
 *
 * Real backend contract (notification.created v1):
 * {
 *   "type": "notification.created",
 *   "notification_id": "uuid-string",
 *   "occurred_at": "ISO8601",
 *   "version": 1
 * }
 *
 * To run: npm run test:ws
 */

import assert from "node:assert/strict";
import { afterEach, beforeEach, describe, it } from "node:test";
import { NotificationWebSocketManager } from "../notification-websocket.manager";

// ── Test fixtures ───────────────────────────────────────────────────────────────

const WS_URL = "ws://localhost:8000/ws/notificaciones/";

/** Minimal valid notification.created event (version 1) — real backend contract */
const VALID_NOTIFICATION_CREATED = JSON.stringify({
  type: "notification.created",
  notification_id: "550e8400-e29b-41d4-a716-446655440001",
  occurred_at: "2026-09-19T10:00:00.000Z",
  version: 1,
});

/** Event with unknown type — should be ignored */
const UNKNOWN_TYPE_EVENT = JSON.stringify({
  type: "notification.unknown",
  foo: "bar",
});

/** Event with wrong version — should be ignored */
const WRONG_VERSION_EVENT = JSON.stringify({
  type: "notification.created",
  notification_id: "550e8400-e29b-41d4-a716-446655440001",
  occurred_at: "2026-09-19T10:00:00.000Z",
  version: 99,
});

/** notification_id is not a non-empty string — should be ignored */
const INVALID_NOTIFICATION_ID = JSON.stringify({
  type: "notification.created",
  notification_id: 123,
  occurred_at: "2026-09-19T10:00:00.000Z",
  version: 1,
});

/** occurred_at is not a valid ISO8601 string — should be ignored */
const INVALID_OCCURRED_AT = JSON.stringify({
  type: "notification.created",
  notification_id: "550e8400-e29b-41d4-a716-446655440001",
  occurred_at: "not-a-date",
  version: 1,
});

/** Not valid JSON — should be ignored */
const INVALID_JSON = "not json at all";

// ── Mock WebSocket ─────────────────────────────────────────────────────────────

type MockWsState = {
  readyState: 0 | 1 | 2 | 3;
  onopen: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent) => void) | null;
  onclose: ((event: CloseEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  url: string;
  close(code?: number, reason?: string): void;
};

const mockWsInstances: MockWsState[] = [];

function makeMockWs(url: string): MockWsState {
  const ws: MockWsState = {
    readyState: 0, // CONNECTING
    onopen: null,
    onmessage: null,
    onclose: null,
    onerror: null,
    url,
    close(code = 1000, reason = "") {
      this.readyState = 3; // CLOSED
      if (this.onclose) {
        this.onclose(new CloseEvent("close", { code, reason, wasClean: true }));
      }
    },
  };
  mockWsInstances.push(ws);
  return ws;
}

function simulateOpen(ws: MockWsState): void {
  ws.readyState = 1; // OPEN
  if (ws.onopen) {
    ws.onopen(new Event("open"));
  }
}

function simulateMessage(ws: MockWsState, data: string): void {
  if (ws.onmessage) {
    ws.onmessage(new MessageEvent("message", { data }));
  }
}

// ── Tests ───────────────────────────────────────────────────────────────────────

describe("NotificationWebSocketManager", () => {
  let manager: NotificationWebSocketManager;

  beforeEach(() => {
    mockWsInstances.length = 0;
    // Use injectable factory so no global patching needed
    manager = NotificationWebSocketManager.createWithFactory(makeMockWs);
  });

  afterEach(() => {
    manager._resetForTesting();
    mockWsInstances.length = 0;
  });

  // ── Test 1: connect idempotence ─────────────────────────────────────────────

  it("connect() is idempotent: calling twice does not create two sockets", () => {
    manager.connect(WS_URL);
    manager.connect(WS_URL); // Should be no-op

    assert.equal(
      mockWsInstances.length,
      1,
      "only one WebSocket should be created",
    );
  });

  // ── Test 2: two subscribers use one socket ─────────────────────────────────

  it("two subscribers share one socket — only one WebSocket created", () => {
    const events1: unknown[] = [];
    const events2: unknown[] = [];

    const unsub1 = manager.subscribe((e) => events1.push(e));
    const unsub2 = manager.subscribe((e) => events2.push(e));

    manager.connect(WS_URL);
    assert.equal(mockWsInstances.length, 1);

    simulateOpen(mockWsInstances[0]);
    simulateMessage(mockWsInstances[0], VALID_NOTIFICATION_CREATED);

    assert.equal(events1.length, 1, "subscriber 1 received event");
    assert.equal(events2.length, 1, "subscriber 2 received same event");

    unsub1();
    unsub2();
  });

  // ── Test 3: intentional disconnect does not reconnect ──────────────────────

  it("disconnect() is intentional: no reconnect scheduled", () => {
    manager.connect(WS_URL);
    simulateOpen(mockWsInstances[0]);

    manager.disconnect();

    // Simulate the socket close event (as if browser closed it after disconnect())
    mockWsInstances[0].close(1000);

    assert.equal(mockWsInstances.length, 1);
    assert.equal(manager.state, "disconnected", "state should be disconnected");
  });

  // ── Test 4: abnormal close schedules reconnect ───────────────────────────────

  it("abnormal close (non-auth code) transitions to reconnecting state", () => {
    // Ensure navigator.onLine is true (Node has no navigator; browser has it)
    const originalOnLine = navigator.onLine;
    Object.defineProperty(navigator, "onLine", {
      value: true,
      configurable: true,
    });

    try {
      manager.connect(WS_URL);
      simulateOpen(mockWsInstances[0]);

      // Abnormal close: server crashed (code 1006)
      mockWsInstances[0].close(1006);

      assert.equal(
        manager.state,
        "reconnecting",
        "state should be reconnecting after abnormal close",
      );
    } finally {
      Object.defineProperty(navigator, "onLine", {
        value: originalOnLine,
        configurable: true,
      });
    }
  });

  // ── Test 5: 4401 / 4403 do NOT reconnect ──────────────────────────────────

  it("close code 4401 (auth) does NOT reconnect", () => {
    manager.connect(WS_URL);
    simulateOpen(mockWsInstances[0]);

    const beforeCount = mockWsInstances.length;

    mockWsInstances[0].close(4401);

    assert.equal(
      manager.state,
      "disconnected",
      "4401 → disconnected (no reconnect)",
    );
    assert.equal(mockWsInstances.length, beforeCount, "no new socket created");
  });

  it("close code 4403 (going away) does NOT reconnect", () => {
    manager.connect(WS_URL);
    simulateOpen(mockWsInstances[0]);

    const beforeCount = mockWsInstances.length;

    mockWsInstances[0].close(4403);

    assert.equal(
      manager.state,
      "disconnected",
      "4403 → disconnected (no reconnect)",
    );
    assert.equal(mockWsInstances.length, beforeCount, "no new socket created");
  });

  // ── Test 6: offline pauses reconnect ───────────────────────────────────────

  it("navigator.onLine === false pauses reconnect", () => {
    manager.connect(WS_URL);
    simulateOpen(mockWsInstances[0]);

    // Save original and patch
    const originalOnLine = navigator.onLine;
    Object.defineProperty(navigator, "onLine", {
      value: false,
      configurable: true,
    });

    try {
      mockWsInstances[0].close(1006);

      assert.equal(
        manager.state,
        "disconnected",
        "offline → disconnected (no reconnect timer)",
      );
    } finally {
      Object.defineProperty(navigator, "onLine", {
        value: originalOnLine,
        configurable: true,
      });
    }
  });

  // ── Test 7: valid event distributed ─────────────────────────────────────────

  it("valid notification.created event (v1) is distributed to subscribers", () => {
    const received: unknown[] = [];
    manager.subscribe((e) => received.push(e));

    manager.connect(WS_URL);
    simulateOpen(mockWsInstances[0]);
    simulateMessage(mockWsInstances[0], VALID_NOTIFICATION_CREATED);

    assert.equal(received.length, 1);
    const event = received[0] as {
      type: string;
      notification_id: string;
      occurred_at: string;
      version: number;
    };
    assert.equal(event.type, "notification.created");
    assert.equal(event.notification_id, "550e8400-e29b-41d4-a716-446655440001");
    assert.equal(event.occurred_at, "2026-09-19T10:00:00.000Z");
    assert.equal(event.version, 1);
  });

  // ── Test 8: invalid events are ignored ─────────────────────────────────────

  it("invalid JSON is ignored without error", () => {
    const received: unknown[] = [];
    manager.subscribe((e) => received.push(e));

    manager.connect(WS_URL);
    simulateOpen(mockWsInstances[0]);
    simulateMessage(mockWsInstances[0], INVALID_JSON);

    assert.equal(received.length, 0, "invalid JSON should be silently ignored");
  });

  it("unknown event type is ignored without error", () => {
    const received: unknown[] = [];
    manager.subscribe((e) => received.push(e));

    manager.connect(WS_URL);
    simulateOpen(mockWsInstances[0]);
    simulateMessage(mockWsInstances[0], UNKNOWN_TYPE_EVENT);

    assert.equal(received.length, 0, "unknown type should be silently ignored");
  });

  it("wrong version event is ignored without error", () => {
    const received: unknown[] = [];
    manager.subscribe((e) => received.push(e));

    manager.connect(WS_URL);
    simulateOpen(mockWsInstances[0]);
    simulateMessage(mockWsInstances[0], WRONG_VERSION_EVENT);

    assert.equal(
      received.length,
      0,
      "wrong version should be silently ignored",
    );
  });

  it("non-string notification_id is ignored without error", () => {
    const received: unknown[] = [];
    manager.subscribe((e) => received.push(e));

    manager.connect(WS_URL);
    simulateOpen(mockWsInstances[0]);
    simulateMessage(mockWsInstances[0], INVALID_NOTIFICATION_ID);

    assert.equal(
      received.length,
      0,
      "non-string notification_id should be ignored",
    );
  });

  it("invalid occurred_at is ignored without error", () => {
    const received: unknown[] = [];
    manager.subscribe((e) => received.push(e));

    manager.connect(WS_URL);
    simulateOpen(mockWsInstances[0]);
    simulateMessage(mockWsInstances[0], INVALID_OCCURRED_AT);

    assert.equal(received.length, 0, "invalid occurred_at should be ignored");
  });
});
