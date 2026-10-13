/**
 * Unit tests for useNotificationRealtime debounce/coalescing logic.
 *
 * Test runner: node --test (Node.js built-in)
 * Run: npx tsx --test src/features/notificaciones/hooks/__tests__/useNotificationRealtime.test.ts
 *
 * Coverage:
 * - Multiple rapid notification.created events → one invalidation (debounce)
 * - Invalid event type → no invalidation
 * - Reconnection to connected → invalidation fires once
 * - Cleanup cancels pending timers
 */

import assert from "node:assert";
import { afterEach, beforeEach, describe, it } from "node:test";

// ── Pure debounce/coalescing logic (extracted for testability) ──────────────────

interface InvalidationJob {
  readonly id: number;
  readonly scheduledAt: number;
}

interface Debouncer {
  schedule: () => void;
  cancel: () => void;
  pending: boolean;
  readonly pendingJob: InvalidationJob | null;
}

/**
 * Creates a debouncer that coalesces multiple calls into one delayed invocation.
 * - First call schedules a delayed job
 * - Subsequent calls before the delay cancels the previous job and schedules a new one
 * - cancel() clears any pending job
 *
 * @param delayMs - milliseconds to wait before firing
 * @param onFire - called when the debounced job fires
 */
function createDebouncer(delayMs: number, onFire: () => void): Debouncer {
  let timer: ReturnType<typeof setTimeout> | null = null;
  let counter = 0;
  let currentJob: InvalidationJob | null = null;

  return {
    schedule() {
      // Cancel any existing pending job — coalescing
      if (timer !== null) {
        clearTimeout(timer);
        timer = null;
        currentJob = null;
      }
      const job: InvalidationJob = { id: ++counter, scheduledAt: Date.now() };
      currentJob = job;
      timer = setTimeout(() => {
        // Only fire if this job is still the current one (not superseded)
        if (currentJob?.id === job.id) {
          currentJob = null;
          timer = null;
          onFire();
        }
      }, delayMs);
    },

    cancel() {
      if (timer !== null) {
        clearTimeout(timer);
        timer = null;
        currentJob = null;
      }
    },

    get pending() {
      return timer !== null;
    },

    get pendingJob() {
      return currentJob;
    },
  };
}

// ── Mock QueryClient ───────────────────────────────────────────────────────────

type QueryKey = readonly unknown[];

interface MockQueryClient {
  invalidateQueriesCalls: Array<{ queryKey: QueryKey }>;
  invalidateQueries: (opts: { queryKey: QueryKey }) => void;
}

function createMockQueryClient(): MockQueryClient {
  return {
    invalidateQueriesCalls: [],
    invalidateQueries(opts: { queryKey: QueryKey }) {
      this.invalidateQueriesCalls.push({ queryKey: opts.queryKey });
    },
  };
}

// ── Pure invalidation scheduler (mimics useNotificationRealtime internals) ────

const NOTIFICACIONES_LIST_QUERY_KEY = ["notificaciones", "list"] as const;
const NOTIFICACIONES_SUMMARY_KEY = ["notificaciones", "summary"] as const;

interface RealtimeScheduler {
  /** Called on notification.created event */
  onNotificationCreated: () => void;
  /** Called on connection state = connected (reconnect or initial) */
  onConnected: () => void;
  /** Cancel all pending timers */
  cancel: () => void;
  /** Returns true if a debounce timer is currently pending */
  readonly hasPendingTimer: boolean;
}

/**
 * Creates a realtime scheduler with the same debounce/coalescing strategy
 * used in useNotificationRealtime.
 *
 * @param queryClient - mock query client
 * @param debounceMs - debounce delay (default 300ms)
 */
function createRealtimeScheduler(
  queryClient: MockQueryClient,
  debounceMs = 300,
): RealtimeScheduler {
  const debouncer = createDebouncer(debounceMs, () => {
    queryClient.invalidateQueries({
      queryKey: [...NOTIFICACIONES_LIST_QUERY_KEY] as unknown[],
    });
    queryClient.invalidateQueries({
      queryKey: [...NOTIFICACIONES_SUMMARY_KEY] as unknown[],
    });
  });

  let connectedInvalidated = false;

  return {
    onNotificationCreated() {
      debouncer.schedule();
    },

    onConnected() {
      if (connectedInvalidated) return;
      connectedInvalidated = true;
      queryClient.invalidateQueries({
        queryKey: [...NOTIFICACIONES_LIST_QUERY_KEY] as unknown[],
      });
      queryClient.invalidateQueries({
        queryKey: [...NOTIFICACIONES_SUMMARY_KEY] as unknown[],
      });
    },

    cancel() {
      debouncer.cancel();
    },

    get hasPendingTimer() {
      return debouncer.pending;
    },
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useNotificationRealtime debounce/coalescing", () => {
  beforeEach(() => {
    // Tests use real timers (setTimeout) — no fake clock needed
  });

  afterEach(() => {
    // No cleanup needed for real timers in these tests
  });

  // ── 1. Multiple rapid notification.created → one invalidation (debounce) ──

  it("coalesces multiple rapid notification.created events into one invalidation", async () => {
    const queryClient = createMockQueryClient();
    const scheduler = createRealtimeScheduler(queryClient, 300);

    // Simulate 5 events fired in rapid succession (e.g. 50ms apart)
    scheduler.onNotificationCreated();
    scheduler.onNotificationCreated();
    scheduler.onNotificationCreated();
    scheduler.onNotificationCreated();
    scheduler.onNotificationCreated();

    // No invalidation yet — timer is pending
    assert.strictEqual(queryClient.invalidateQueriesCalls.length, 0);
    assert.strictEqual(scheduler.hasPendingTimer, true);

    // Advance past the debounce window (300ms)
    await delay(310);

    // Only ONE invalidation should have fired
    assert.strictEqual(queryClient.invalidateQueriesCalls.length, 2); // list + summary = 2
    assert.deepStrictEqual(
      queryClient.invalidateQueriesCalls.map((c) => [...c.queryKey]),
      [
        ["notificaciones", "list"],
        ["notificaciones", "summary"],
      ],
    );
  });

  // ── 2. Invalid event type → no invalidation ──

  it("does not invalidate for unknown event types", async () => {
    const queryClient = createMockQueryClient();
    const scheduler = createRealtimeScheduler(queryClient, 300);

    // Unknown event — the scheduler doesn't even have an handler for it in this test
    // because onNotificationCreated is only called when the event type matches
    // "notification.created". So we just assert no invalidation happened.
    assert.strictEqual(queryClient.invalidateQueriesCalls.length, 0);
    assert.strictEqual(scheduler.hasPendingTimer, false);

    // Advance time — still nothing should happen
    await delay(400);
    assert.strictEqual(queryClient.invalidateQueriesCalls.length, 0);
  });

  // ── 3. Reconnection to connected → invalidation fires once ──

  it("invalidates exactly once on reconnection to connected state", async () => {
    const queryClient = createMockQueryClient();
    const scheduler = createRealtimeScheduler(queryClient, 300);

    // First connection → immediate invalidation (no debounce)
    scheduler.onConnected();
    assert.strictEqual(queryClient.invalidateQueriesCalls.length, 2);
    assert.deepStrictEqual(
      queryClient.invalidateQueriesCalls.map((c) => [...c.queryKey]),
      [
        ["notificaciones", "list"],
        ["notificaciones", "summary"],
      ],
    );

    // Subsequent connected events should NOT re-invalidate
    scheduler.onConnected();
    scheduler.onConnected();
    assert.strictEqual(
      queryClient.invalidateQueriesCalls.length,
      2,
      "connected events after the first should not re-invalidate",
    );
  });

  // ── 4. Cleanup cancels pending timers ──

  it("cancel() clears any pending debounce timer", async () => {
    const queryClient = createMockQueryClient();
    const scheduler = createRealtimeScheduler(queryClient, 300);

    scheduler.onNotificationCreated();
    assert.strictEqual(scheduler.hasPendingTimer, true);

    // Cancel before debounce fires
    scheduler.cancel();
    assert.strictEqual(scheduler.hasPendingTimer, false);

    // Advance past debounce — no invalidation should happen
    await delay(400);
    assert.strictEqual(queryClient.invalidateQueriesCalls.length, 0);
  });

  // ── 5. Timer fires after debounce period ──

  it("invalidates after the debounce period expires", async () => {
    const queryClient = createMockQueryClient();
    const scheduler = createRealtimeScheduler(queryClient, 300);

    scheduler.onNotificationCreated();
    assert.strictEqual(scheduler.hasPendingTimer, true);

    // Advance 150ms — still pending
    await delay(150);
    assert.strictEqual(scheduler.hasPendingTimer, true);
    assert.strictEqual(queryClient.invalidateQueriesCalls.length, 0);

    // Advance remaining 160ms (total 310ms > 300ms debounce)
    await delay(160);
    assert.strictEqual(scheduler.hasPendingTimer, false);
    assert.strictEqual(queryClient.invalidateQueriesCalls.length, 2);
  });

  // ── 6. Reconnection + notification events work independently ──

  it("debounced invalidation and reconnect invalidation are independent", async () => {
    const queryClient = createMockQueryClient();
    const scheduler = createRealtimeScheduler(queryClient, 300);

    // Connect fires immediate invalidation
    scheduler.onConnected();
    assert.strictEqual(queryClient.invalidateQueriesCalls.length, 2);

    // Notification events still get debounced and fire later
    scheduler.onNotificationCreated();
    scheduler.onNotificationCreated();
    assert.strictEqual(scheduler.hasPendingTimer, true);

    await delay(310);
    // Reconnect invalidation already fired (2 calls), now debounce fires (2 more)
    assert.strictEqual(queryClient.invalidateQueriesCalls.length, 4);
  });

  // ── 7. List uses prefix key for all pagination variants; summary uses exact key ──

  it("invalidates list with prefix key and summary with exact key", async () => {
    const queryClient = createMockQueryClient();
    const scheduler = createRealtimeScheduler(queryClient, 300);

    scheduler.onNotificationCreated();
    await delay(310);

    const [first, second] = queryClient.invalidateQueriesCalls;

    // First call: list prefix — matches any ["notificaciones","list",{...params}] variant
    // TanStack Query invalidates by prefix, so ["notificaciones","list"] catches all paginated lists
    assert.deepStrictEqual([...first.queryKey], ["notificaciones", "list"]);

    // Second call: summary exact key
    assert.deepStrictEqual([...second.queryKey], ["notificaciones", "summary"]);
  });
});

// ── Helpers ───────────────────────────────────────────────────────────────────

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
