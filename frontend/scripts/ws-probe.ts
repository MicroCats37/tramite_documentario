/**
 * ws-probe — WebSocket diagnostic tool for notificaciones-websocket-channels.
 *
 * Tests backend WebSocket endpoint and consumer/publisher without a browser.
 *
 * Usage:
 *   JWT_TOKEN=... USER_ID=25 WS_URL=... AUTH_STORAGE_PREFIX=... npx tsx frontend/scripts/ws-probe.ts
 *
 * Required env vars:
 *   JWT_TOKEN          — JWT access token
 *   USER_ID            — integer user ID
 *   WS_URL             — WebSocket URL (e.g. ws://localhost:8000/ws/notificaciones/)
 *   AUTH_STORAGE_PREFIX — cookie prefix (e.g. tramite_documentario_auth)
 */

import WebSocket from "ws";

const WS_URL = process.env.WS_URL;
const AUTH_STORAGE_PREFIX = process.env.AUTH_STORAGE_PREFIX;
const JWT_TOKEN = process.env.JWT_TOKEN ?? "";
const USER_ID = parseInt(process.env.USER_ID ?? "", 10);
const TIMEOUT_MS = parseInt(process.env.TIMEOUT_MS ?? "30000", 10);

if (!JWT_TOKEN) {
  console.error("[ws-probe] ERROR: JWT_TOKEN env var is required.");
  process.exit(1);
}
if (!WS_URL) {
  console.error("[ws-probe] ERROR: WS_URL env var is required (e.g. ws://localhost:8000/ws/notificaciones/).");
  process.exit(1);
}
if (!AUTH_STORAGE_PREFIX) {
  console.error("[ws-probe] ERROR: AUTH_STORAGE_PREFIX env var is required (e.g. tramite_documentario_auth).");
  process.exit(1);
}

const AUTH_COOKIE_NAME = `${AUTH_STORAGE_PREFIX}_access_token`;

if (Number.isNaN(USER_ID)) {
  console.error(
    "[ws-probe] ERROR: USER_ID must be an integer. Got:",
    process.env.USER_ID,
  );
  process.exit(1);
}

console.log("[ws-probe] Connecting to:", WS_URL);
console.log(
  "[ws-probe] Cookie:",
  `${AUTH_COOKIE_NAME}=${JWT_TOKEN.slice(0, 12)}...`,
);
console.log("[ws-probe] User ID:", USER_ID);
console.log("[ws-probe] Timeout:", TIMEOUT_MS, "ms");
console.log("---");

const socket = new WebSocket(WS_URL, {
  headers: {
    Cookie: `${AUTH_COOKIE_NAME}=${JWT_TOKEN}`,
  },
});

const timeout = setTimeout(() => {
  console.log(`[ws-probe] TIMEOUT after ${TIMEOUT_MS}ms — closing.`);
  socket.close();
  process.exit(0);
}, TIMEOUT_MS);

socket.on("open", () => {
  console.log("[ws-probe] ✓ CONNECTED");
});

socket.on("message", (data: WebSocket.RawData) => {
  const text = data.toString();
  console.log("[ws-probe] MESSAGE:", text);
  try {
    const parsed = JSON.parse(text);
    console.log("[ws-probe]   parsed:", JSON.stringify(parsed, null, 2));
  } catch {
    // not JSON
  }
});

socket.on("close", (code: number, reason: Buffer) => {
  clearTimeout(timeout);
  console.log(
    `[ws-probe] ✗ CLOSED — code=${code} reason=${reason.toString() || "(none)"}`,
  );
  process.exit(0);
});

socket.on("error", (err: Error) => {
  clearTimeout(timeout);
  console.error("[ws-probe] ERROR:", err.message);
  process.exit(1);
});

process.on("SIGINT", () => {
  console.log("\n[ws-probe] Caught Ctrl+C — closing socket.");
  socket.close();
  process.exit(0);
});
