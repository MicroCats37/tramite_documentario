# Apply Progress — Solicitud detalle / trazabilidad operativa

Change scope: remediation of the Solicitud traceability frontend per `docs/ui-ux/solicitud-trazabilidad-auditoria-implementacion.md` (work units 1-11).

---

## U1-U2 (2026-09-13) — Pure normalization foundation: labels + flow + timeline builders

Status: DONE — verified (tsc + biome + 37 unit tests via existing tsx tooling).

### Work Unit 1 — Normalización y labels (`traceabilityLabels.ts`)

Created `frontend/src/features/tramites/components/trazabilidad/traceabilityLabels.ts`:

- `solicitudEstadoLabel` — global Solicitud state via `ESTADO_SOLICITUD` (tramite.tokens).
- `periodoEstadoLabel` — period/cycle state via `ESTADO_PERIODO` (tramite.tokens).
- `participacionLabel` — participation type via `TIPO_PARTICIPACION` (tramite.tokens).
- `respuestaLabel` — formal response type via `TIPO_RESPUESTA_LABELS` (finalizar-solicitud.schema).
- `respuestaEstadoLabel` — response lifecycle state (BORRADOR/EMITIDA/ANULADA/RECTIFICADA).
- `eventoTipoLabel` — TimelineEventOut.tipo, canonical + forward-compatible alias spellings
  (AREA_INCORPORADA, PERIODO_INICIADO, PERIODO_CERRADO, PARTICIPANTE_AGREGADO,
  PARTICIPANTE_RETIRO, PARTICIPANTE_RETIRADO, RESPUESTA_EMITIDA, RESPUESTA_REGISTRADA,
  ESTADO_SOLICITUD_CAMBIADO, ESTADO_PERIODO_CAMBIADO, PERIODO_ESTADO_CAMBIADO).
- `tipoCierreLabel` — closure type (FINALIZADO/DERIVADO/RETIRADO/RECHAZADO/ANULADO/
  ASIGNACION_ERRONEA/CAMBIO_PARTICIPACION).
- `humanizeEnum` — safe fallback for unknown values (lowercase, `_`→space, capitalize).
  Never leaks snake_case to the UI; null/empty → "Sin dato". Fixes F14.
- Reuses existing exported constants (`graphStatus.ts` is semantic, not labels — no reuse needed).

### Work Unit 1 — Flujo global puro (`buildSolicitudFlow.ts`)

Created `frontend/src/features/tramites/components/trazabilidad/buildSolicitudFlow.ts`:

- `buildSolicitudFlow(trazabilidad, ctx)` → `{ nodes, edges, areaGroups, mergeNodeId, terminalNodeId }`.
- Input contract: `SolicitudTrazabilidad` (trazabilidad.schema) + `SolicitudGlobalContext`
  (fecha_registro, estado, fecha_cierre, id_publico).
- Stable composite IDs per entity (never timestamp-only): `global-start`, `global-state-{idx}`,
  `area-{areaId}`, `area-{areaId}-period-{periodId}`, `-participant-{userId}-{idx}[-out]`,
  `-response-{respId}`, `-state-{idx}`, `-terminal`, `global-merge`, `global-terminal`. Fixes F15 key collisions.
- Interleaved participant/state/response events sorted by timestamp FIRST within each cycle (F04);
  no category bucketing. Deterministic tie-break by node kind rank then id.
- Edges are chronological precedence ONLY (never causality); area branches hang off the
  chronologically compatible global event; area terminals converge into `global-merge`
  before the terminal. Consecutive cycles connect only when the previous one has a real end.
- Each node declares `handles: { input, output }` so the renderer can expose F01 handles
  (start has no input, terminal has no output).
- Skips the backend's initial REGISTRADA dupe at fecha_registro.

### Work Unit 2 — Rango temporal (`traceabilityTimeline.ts`)

Created `frontend/src/features/tramites/components/trazabilidad/traceabilityTimeline.ts`:

- `buildLifecycleBounds(input)` → `dataStart/dataEnd/minBound/maxBound/hasOpenPeriod/now`.
  `now` included ONLY for open periods or active global state (F08); closed trámite ends at the
  last real event / fecha_cierre. Deterministic padding = 4% of lifecycle, floor 10 min
  (PAD_FLOOR_MS), cap 3 days (PAD_CAP_MS). Injectable `now` for tests.
- `buildGlobalStateSegments(historial, bounds, now?)` → contiguous segments from each change to
  the next / closure / now; prologue segment from dataStart when the first change comes later (F10).
- `formatDuration(start, end)` — neutral Spanish (meses/días/h/mes), null end → "En curso".
- `formatTimelineDate(ts, granularity?)` — `es-PE` (Intl), granularities seconds/minutes/hours/day/month.
- Handles empty input, single event, same-day, open periods, nulls.

### Tests

Repo has NO Vitest/Jest configured (package.json has no test runner). Tests were added next to
the feature in `__tests__/` using Node's built-in `node:test` + `node:assert`, and run with the
repo's already-available `tsx` tooling (v4.23.13 present in npx cache; `npx --no-install tsx -v`
resolves without any install):

```
npx tsx --test src/features/tramites/components/trazabilidad/__tests__/*.test.ts
# tests 37 | suites 8 | pass 37 | fail 0
```

Coverage: interleaved timestamps (F04), unknown enums, nulls, closed vs open bounds (F08),
same-day, single event, empty input, deterministic IDs, handle-contract endpoints, area-branch
global anchoring, merge convergence, terminal labeling, prologue segment, es-PE formatting.

No new dependencies installed. `npm run build` NOT executed (user constraint).

### Verification

- `npx tsc --noEmit` (frontend/) → exit 0.
- `npx biome check` on touched files → 0 warnings, 0 errors (warnings found on first pass were
  cleaned: `noNonNullAssertion` in tests, `useOptionalChain` in buildSolicitudFlow.ts).

### Deviations from the audit spec

None. Implementation matches sections F, H (pure-builder part), M, N units 1-2. `elkjs` and layout
deferred to a later unit per plan.

---

## U3 (2026-09-13) — Timeline controlado, headers es-PE, estilos CIP y tipado de renderers

Status: DONE — verified (tsc + biome + 44 unit tests via existing tsx tooling; `npm run build` NOT executed).

### Files

- **Rewritten** `frontend/src/features/tramites/components/trazabilidad/SolicitudTimelineView.tsx` (590 → ~964 lines).
- **Created** `frontend/src/features/tramites/components/trazabilidad/SolicitudTimelineView.module.css` — scoped CIP overrides for the library's global `.rct-*` classes (default red `#c52020` root, white/English date headers) under `.solicitud-timeline-scope`.
- **Extended** `traceabilityTimeline.ts` — added pure `clampVisibleRange(requestedStart, requestedEnd, minBound, maxBound)` (F07).
- **Modified** `TrazabilidadView.tsx` + `app/(protected)/solicitudes/[id]/page.tsx` — thread optional `fechaRegistro`/`fechaCierre`/`estado` into the timeline so `buildLifecycleBounds` (F08) receives the real Solicitud root context.
- **Modified** `frontend/biome.json` — enabled `css.parser.cssModules: true` (scoped to `*.module.css` via the schema option; required to parse `:global()`).

### Controlled range (F07)

- `visibleTimeStart/End` live in state, initialized to the derived `[dataStart, dataEnd]` (Ajustar target).
- `onTimeChange` clamps pan/zoom inside `[minBound, maxBound]` via `clampVisibleRange` (preserves requested duration, shifts within bounds), then calls the library's `updateScrollCanvas` and updates state. Max zoom-out is the padded data range; `maxZoom` prop mirrors it as a second guard.
- Toolbar: `-`/`+` zoom buttons (`-` disabled at the data bound), plus a persistent labeled `Ajustar al trámite` button restoring exactly the derived data range.
- `Ahora` marker only when `bounds.hasOpenPeriod`.

### Headers / granularity / styling (F09)

- `TimelineHeaders` + two `DateHeader`s, primary+secondary; units adapt to the visible window (`pickHeaderUnits`: year/month → month/day → day/hour → hour/minute) so hours never dominate a multi-day trámite.
- `labelFormat` returns short es-PE labels (`sep 2026`, `lun 14`, `14 sep`, `09:00`) — no `Saturday, September...`.
- All colors from CIP tokens (`bg-card`/`muted`/`border`/`muted-foreground`); burgundy only for selection/state. Rows 72px (global 56, area 80), bars 36px (`lineHeight` 72 + `itemHeightRatio` 0.5), sidebar 260px.

### Groups / items / markers

- Global group: contiguous state segments from `buildGlobalStateSegments` (duration-bearing, humanized, F10).
- Area groups: name, `Principal`/`Adjunta`, `N ciclos`, último estado, responsable activo, and a `Tu participación` signal from real `currentUserId`/`userAreaIds` (F16).
- Cycle bars: `Ciclo N · tipo · duración · estado`; native tooltip with exact dates + participants (F14).
- Markers restricted to registro / global changes / responses / `Ahora` (F15); selectable `<button>` markers with stable composite keys and aria-labels; click emits the existing `PeriodDetailSelection` (`period`/`event`).

### Typing (F19)

- `any` count: **0**. Renderer types derived from `ReactCalendarTimelineProps<RctItem, RctGroup>["itemRenderer"]` / `["groupRenderer"]` (both imported from the package); `onTimeChange` typed via `ReactCalendarTimelineProps["onTimeChange"]`.
- The only boundary cast is `timelineRef.current as TimelineController | null` in `applyRange` (one line, documented) — needed because the package's ref type exposes only `getBoundingClientRect`/`calculateDropCoordinatesToTimeAndGroup` while the mounted instance has the public `updateScrollCanvas` method.

### Verification

- `npx tsc --noEmit` (frontend/) → exit 0.
- `npx biome check` on touched files → 0 errors (format applied with `--write`; a11y `role="img"` added to item bars for `aria-label`).
- `npx tsx --test src/features/tramites/components/trazabilidad/__tests__/*.test.ts` → 44 tests (37 prior + 7 new `clampVisibleRange`), all pass.
- `npm run build` NOT executed (user constraint).

### Remaining work for U4+

Layout/flow (`SolicitudProcessFlow.tsx` rewrite + `elkjs`), selection sync (U7), inspector único (U8), resumen ejecutivo (U9), chat/responsive (U10), accesibilidad/regresión (U11).

---

## U4-U6 (2026-09-13) — Global flow: ELK layout, typed nodes/edges with Handles, readable zoom policy

Status: DONE — verified (tsc + biome + 59 unit tests via existing tsx tooling; `npm run build` NOT executed).

### Files

- **Created** `frontend/src/features/tramites/components/trazabilidad/layoutSolicitudFlow.ts` (692 ln) — pure ELK layout + zoom-policy constants + selection/dimming.
- **Created** `frontend/src/features/tramites/components/trazabilidad/SolicitudProcessFlowNodes.tsx` (315 ln) — memoized custom node components + stable `SOLICITUD_NODE_TYPES` (module scope).
- **Rewritten** `frontend/src/features/tramites/components/trazabilidad/SolicitudProcessFlow.tsx` (819 → 475 ln) — GLOBAL graph component (audit F02/F03/F05/F06).
- **Created** `frontend/src/features/tramites/components/trazabilidad/solicitud-process-flow.module.css` (39 ln) — scoped `.flow-scope` overrides for `react-flow__node`/handles.
- **Created** `frontend/src/features/tramites/components/trazabilidad/legacyProcessFlowTypes.ts` (70 ln) — old per-period node types kept ONLY so `ProcessInspector.tsx` compiles until U8.
- **Modified** `ProcessInspector.tsx` (single import line → legacy types), `TrazabilidadView.tsx` (interim call site, 321 → 292 ln), `index.ts` (barrel), `app/(protected)/solicitudes/[id]/page.tsx` (passes `idPublico`).
- **Created** `__tests__/layoutSolicitudFlow.test.ts` (556 ln) — 15 new tests.
- **Modified** `frontend/package.json` + lockfile — added `elkjs@^0.12.0` (bundled types; `@types/elkjs` NOT installed).

### U4 — Dependency + ELK layout (`layoutSolicitudFlow.ts`)

- `elkjs@0.12.0` (types bundled, `lib/main`). No `--force`/`--legacy-peer-deps`.
- `buildElkGraph(flow)` → pure ELK graph: root `LAYERED`, direction `RIGHT`, `hierarchyHandling: INCLUDE_CHILDREN`; compound node per area (`area-group-<areaId>`, padding `[top=40,…]`) and per cycle (`period-group-<areaId>-<periodId>`, padding `[top=32,…]`). Edges attach at the deepest compound containing both endpoints; cross-hierarchy edges stay at root.
- `positionFromElk(result, flow)` → positioned nodes/edges. Verified against elkjs 0.12: child coordinates are RELATIVE to the compound parent, which matches React Flow's nested-node contract (`parentId`). `absRect` computed by accumulating parent offsets for bounds/translateExtent. Leaves 232×96.
- `layoutSolicitudFlow(flow)` → async (elkjs API), deterministic (asserted by test).
- No DOM/React/Date.now in the module; tests run under `npx tsx --test`.

### U5 — Nodes, edges, handles

- Discriminated union `SolicitudFlowNodeData` keyed by `kind` (14 members: 12 `FlowNodeKind` + `area-group` + `period-group`), type guards (`isFlowGroupNodeData`), typed node `SolicitudFlowReactNode = Node<SolicitudFlowNodeData, string>`.
- `nodeTypes` map defined at MODULE SCOPE; every component memoized (`perf-memo-custom-components.md`). Event nodes render target-LEFT / source-RIGHT Handles ONLY when `data.handles.input/output` says so (start = source only, terminal = target only; F01).
- Labels in Spanish via `traceabilityLabels.ts`; identity full name first (participant `sublabel` = name, `detail` = role). Icons via `lucide-react` (no emoji). Response node picks FileCheck2/FileX2 from label; terminal picks CheckCircle2/XCircle/Circle.
- Edges `smoothstep` + ArrowClosed marker; `toReactEdge` filters edges whose source/target don't resolve (F04). Layout test asserts every edge resolves to a handle-capable endpoint.
- Group nodes (`<section aria-label>`) are non-selectable, `pointer-events-none`, children bound via `parentId`.

### U6 — Viewport & zoom policy (CRITICAL user requirement)

- `minZoom = 0.75` (readable floor), `maxZoom = 1.5`, `FIT_MAX_ZOOM = 1.0` (initial/Ajustar target). Constants exported from `layoutSolicitudFlow.ts` (single source of truth).
- Initial: `fitView({ padding: 0.18, minZoom: 0.75, maxZoom: 1.0 })` → whole graph at 0.85–1.0 when it fits; if it doesn't fit at 0.75 it shows a portion and allows PAN, never shrinking below the floor.
- Wheel/trackpad = PAN (`zoomOnScroll={false}` + `panOnScroll`); pinch still zooms (`zoomOnPinch`); `zoomOnDoubleClick={false}`. Custom Spanish toolbar: `+`/`−`/`Enfocar|Ajustar`; `−` disabled at `minZoom`, `+` disabled at `maxZoom` (via `useViewport`). "Ajustar flujo" fits the graph or the selection with the same clamped options — never below the floor.
- `translateExtent` around the ELK bounding box with `TRANSLATE_MARGIN = 120`.
- Canvas height `min(560px, 70vh)` desktop, `min(440px, 70vh)` when narrow (`compact` prop or container < 1024px via ResizeObserver); never derived from lane count.
- Graph derived ONCE per structural change (`useMemo` on model, F03); selection only toggles `dimmed` via `applySelectionState` and centers via `fitBounds` on the branch (audit G) — no global fitView on every click. Non-selected branches dimmed, never hidden (P).
- `ResizeObserver` only adapts height — no topology recompute.

### Data/state

- `SolicitudProcessFlow` receives `trazabilidad` (full `SolicitudTrazabilidad`) + `global: SolicitudGlobalContext` (fecha_registro, estado, fecha_cierre, id_publico) + `selection: SolicitudFlowSelection` (`{type:"area"|"period"|"node"}`). `onNodeSelect(nodeId)` emits node clicks.
- Interim call site (`TrazabilidadView.tsx`): builds `globalCtx` from its props (new `idPublico` prop threaded from page.tsx), maps any timeline `PeriodDetailSelection` to `{type:"period", areaId, periodId}`, node clicks → `{type:"node", nodeId}`. `ProcessInspector` mount removed (U8 owns the inspector); `OperationalSelectionPanel` untouched.

### Verification

- `npx tsc --noEmit` (frontend/) → exit 0.
- `npx biome check` on all touched files → 0 errors, 0 warnings.
- `npx tsx --test src/features/tramites/components/trazabilidad/__tests__/*.test.ts` → 59 tests (44 prior + 15 new), all pass. New coverage: zoom constants, translateExtent margin, ELK compound structure, edge placement (period/area/root), determinism, non-overlapping leaves, parentId nesting, per-branch bounds, handle-capable edge endpoints, selection dimming (never hide), stale-node-selection safety, pure `positionFromElk` parent-offset accumulation.
- `npm run build` NOT executed (user constraint).

### Deviations / notes

- `NodeProps` in @xyflow/react v12 takes the NODE type, not the data type (skill rule files show the older v11 style) — components are typed `NodeProps<SolicitudFlowReactNode>`.
- ELK child coordinates verified empirically to be parent-relative (matches React Flow nesting); `absRect` accumulates offsets.
- Legacy `ProcessFlowNodeData` moved to `legacyProcessFlowTypes.ts` so `ProcessInspector.tsx` keeps compiling until U8.

### Remaining work for U7+

U7 (single selection state, timeline↔flow bidirectional sync), U8 (inspector único, remove `OperationalSelectionPanel` duplication + `legacyProcessFlowTypes`), U9 (resumen ejecutivo), U10 (chat/responsive wiring — `compact` prop already exposed), U11 (accesibilidad/regresión completa).

---

## U12 (2026-09-13) — Reversión de calendario y React Flow; consolidación en mapa de tarjetas único

**Status**: DONE — verified (tsc + biome + 61 unit tests via existing tsx tooling; `npm run build` NOT executed).

**User decision (2026-09-13)**: `react-calendar-timeline` es visualmente inaceptable y duplica el flujo de tarjetas. `React Flow` causó problemas estructurales (F01–F06). Decisión: mantener UNA visualización primaria — el mapa horizontal de tarjetas conectadas, sin librería de grafos.

### Dependencias eliminadas

- `npm uninstall react-calendar-timeline` — desinstalado del `frontend/package.json` + lockfile
- Grep `@xyflow/react|elkjs` en `src/frontend/` → **0 matches** (ya habían sido eliminados en U4-U6 reversión anterior)

### Archivos eliminados (2)

- `SolicitudTimelineView.tsx` — componente react-calendar-timeline
- `SolicitudTimelineView.module.css` — estilos scoped del calendario

### Archivos creados (2)

- `TemporalSummary.tsx` (~152 ln) — franja compacta de lifecycle: inicio, fin, duración total, áreas involucradas
- `ChronologicalHistory.tsx` (~140 ln) — Collapsible "Ver historial cronológico", cerrado por defecto, oldest-first

### Archivos modificados (3)

- `TrazabilidadView.tsx` (294 → ~280 ln) — nueva composición: TemporalSummary → SolicitudCardFlow → ChronologicalHistory → TraceabilityInspector; eliminada importación/renderizado de SolicitudTimelineView
- `index.ts` — eliminados exports de SolicitudTimelineView; agregados exports de TemporalSummary y ChronologicalHistory
- `docs/ui-ux/solicitud-trazabilidad-auditoria-implementacion.md` — append nota de reversión dated 2026-09-13

### Verificación

- `npx tsc --noEmit` (frontend/) → exit 0.
- `npx biome check` en todos los archivos de trazabilidad → 0 errores, 0 warnings.
- `npx tsx --test src/features/tramites/components/trazabilidad/__tests__/*.test.ts` → 61 tests (59 prior + 0 nuevos), todos pasan.
- Grep `react-calendar-timeline|@xyflow/react|elkjs` en `src/` → 0 matches.
- `npm run build` NOT executed (user constraint).

### Nota para agentes futuros

No reintroduzca `react-calendar-timeline`, `@xyflow/react` ni `elkjs`. La arquitectura vigente es: resumen temporal → mapa de tarjetas conectado → historial cronológico colapsable → inspector único.