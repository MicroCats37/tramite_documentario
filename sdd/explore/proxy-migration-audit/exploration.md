## Exploration: Proxy migration completeness audit

### Migration Status by File

| File | Status |
|------|--------|
| `frontend/src/lib/api.ts` | OK — baseURL uses `NEXT_PUBLIC_API_URL \|\| "/backend"` correctly |
| `frontend/src/lib/utils.ts` | **ISSUE** — `resolveImageUrl` creates `/backend/media/` paths but nginx has no matching location (see Gap #1) |
| `frontend/src/app/api/auth/refresh/route.ts` | OK — fallback to `http://localhost:12001` is reasonable dev fallback; production uses `BACKEND_API_URL` from env |
| `frontend/next.config.ts` | OK — fallback to `http://localhost:12001` for dev; env var correctly injected in Docker |
| `frontend/src/features/notificaciones/services/notification-websocket.manager.ts` | OK — browser fallback to `ws://${host}/ws/notificaciones/` is correct for proxy; server-side fallback unreachable in normal usage |
| `frontend/src/lib/auth/cookies.ts` | OK — uses `AUTH_STORAGE_PREFIX` from `NEXT_PUBLIC_AUTH_STORAGE_PREFIX` consistently |
| `backend/config/settings/base.py` | OK — `AUTH_STORAGE_PREFIX`, `FILE_PROXY_URL`, all SAAA vars present with env defaults |
| `backend/config/settings/production.py` | OK — CORS settings use env; `CSRF_TRUSTED_ORIGINS` includes proxy port 7000 |
| `docker-compose.yml` | **ISSUE** — `MEDIA_URL` fallback hardcoded to `http://10.10.5.177:12001/media/` (see Gap #2) |
| `proxy/nginx.conf` | **ISSUE** — `/media/` location exists but `/backend/media/` not routed (see Gap #1) |
| `backend/config/urls.py` | OK — comment only |
| `backend/core_application/storage/resolvers.py` | OK — handles relative and absolute `FILE_PROXY_URL`; comments only |
| `frontend/scripts/ws-probe.ts` | LOW — hardcoded `ws://localhost:12001` defaults; dev-only diagnostic tool |
| `.env.example` | **ISSUE** — `SAAA_USE_FAKE` not documented (see Gap #4); `BACKEND_API_URL` missing |

---

### Gaps Found

1. **[severity: high] `frontend/src/lib/utils.ts:11` + `proxy/nginx.conf` — Media URL routing mismatch (Phase 3 regression)**

   `resolveImageUrl` prepends `NEXT_PUBLIC_API_URL` (`/backend`) to relative media paths, producing `/backend/media/...` URLs. But nginx has `location /media/` (proxies to `backend_upstream`) and `location /backend/` (rewrites to `backend_upstream/api/`). The `/backend/media/...` path is not handled — nginx falls through to the catchall `/` → frontend → 404.

   **In production with `DEBUG=False` and `MEDIA_URL=/media/`**: Django `FileField.url` returns relative `/media/...` paths. `resolveImageUrl` transforms these to `/backend/media/...` which 404s.

   **In dev with `DEBUG=True` and `MEDIA_URL=http://localhost:12001/media/`**: Django returns absolute URLs, `resolveImageUrl` returns them unchanged, and the browser calls `http://localhost:12001/media/...` directly (bypassing proxy). Works in dev but breaks the proxy path.

   **Fix options**:
   - A) Add nginx `location /backend/media/` that proxies to `backend_upstream` without the `/api/` prefix, OR
   - B) Change `resolveImageUrl` to NOT prepend `/backend` for media paths — have nginx serve `/media/` directly and remove the `/backend` prefix from media URLs entirely.

2. **[severity: high] `docker-compose.yml:67` — `MEDIA_URL` hardcoded fallback to old IP**

   ```yaml
   MEDIA_URL: ${MEDIA_URL:-http://10.10.5.177:12001/media/}
   ```

   `10.10.5.177` is a legacy IP from a previous network configuration, not updated in Phase 3. Since `.env.example` does NOT define `MEDIA_URL`, this fallback is used in Docker.

   **Fix**: Change to `${MEDIA_URL:-http://backend:8000/media/}` (uses Docker DNS) or simply `${MEDIA_URL:-/media/}` and ensure nginx proxies `/media/` correctly.

3. **[severity: medium] `frontend/src/features/notificaciones/services/notification-websocket.manager.ts:218` — Server-side WS fallback**

   ```typescript
   return "ws://localhost:12001/ws/notificaciones/";
   ```

   Server-side (edge case) fallback uses hardcoded `localhost:12001`. Won't trigger in normal browser usage (line 215 browser fallback used first), but is architecturally inconsistent. Should use an env var or at minimum `NEXT_PUBLIC_WS_URL`.

4. **[severity: medium] `frontend/scripts/ws-probe.ts:21,23` — Hardcoded WS URL and cookie name**

   - `WS_URL` defaults to `ws://localhost:12001/ws/notificaciones/`
   - Auth cookie name hardcoded to `tramite_documentario_auth_access_token` instead of reading from `AUTH_STORAGE_PREFIX`

   Dev-only diagnostic tool, not deployed, but should be consistent.

5. **[severity: low] `.env.example` — `SAAA_USE_FAKE` not documented**

   `SAAA_USE_FAKE` is read by `backend/core_application/storage/services/abstract_storage.py` and `backend/modules/tramites/di.py` but is only a commented-out line in `.env.example` (line 110). Should be documented with its semantics.

6. **[severity: low] `.env.example` — `BACKEND_API_URL` not listed as a frontend env var**

   `BACKEND_API_URL` is used by `frontend/src/app/api/auth/refresh/route.ts` and `frontend/next.config.ts` as the server-side backend URL. It's defined in docker-compose.yml for the frontend service but not listed in `.env.example` as a frontend-relevant env var (only `NEXT_PUBLIC_API_URL` is). Should be documented in the "Backend server-side" section alongside `MEDIA_URL`.

---

### Hardcoded URLs Found

| File:line | Value | Type | Risk |
|-----------|-------|------|------|
| `docker-compose.yml:67` | `http://10.10.5.177:12001/media/` | Media URL fallback | **HIGH** — legacy IP not updated in Phase 3 |
| `notification-websocket.manager.ts:218` | `ws://localhost:12001/ws/notificaciones/` | WS fallback | **LOW** — server-side edge case |
| `ws-probe.ts:21` | `ws://localhost:12001/ws/notificaciones/` | WS default | **LOW** — dev tool only |
| `backend/config/urls.py:25` | Comment: `http://localhost:12001/media/` | Documentation | None — comment only |
| `backend/config/settings/base.py:116` | Comment: `http://localhost:12001/api/archivo/public/` | Documentation | None — comment only |
| `backend/core_application/storage/resolvers.py:29,43,94` | Comment examples | Documentation | None — comment only |
| `test_storage_resolvers.py` + `test_expediente_archivo_url.py` | Test data hardcoded URLs | Test fixtures | None — test only |

---

### Env Var Coverage

| Env var | Used by | In `.env.example`? |
|---------|---------|-------------------|
| `NEXT_PUBLIC_API_URL` | `api.ts`, `utils.ts` | ✅ Yes (line 63) |
| `NEXT_PUBLIC_AUTH_STORAGE_PREFIX` | `cookies.ts` | ✅ Yes (line 66) |
| `NEXT_PUBLIC_COOKIE_SECURE` | Auth code | ✅ Yes (line 69) |
| `NEXT_PUBLIC_IS_TEST_UUID` | Auth/code | ✅ Yes (line 72) |
| `NEXT_PUBLIC_DEBUG_GENERIC_FORM_ERRORS` | Forms | ✅ Yes (line 75) |
| `NEXT_PUBLIC_WS_URL` | WS manager | ✅ Yes (line 80) |
| `BACKEND_API_URL` | `route.ts`, `next.config.ts` | ⚠️ Missing from `.env.example` |
| `MEDIA_URL` | Django FileField | ⚠️ Missing from `.env.example` — only set in docker-compose.yml |
| `FILE_PROXY_URL` | `resolvers.py` | ✅ Yes (line 96) |
| `AUTH_STORAGE_PREFIX` | Django settings | ✅ Yes (line 124) |
| `SAAA_URL` | Storage service | ✅ Yes (line 103) |
| `SAAA_APP_ID` | Storage service | ✅ Yes (line 104) |
| `SAAA_USUARIO_ID` | Storage service | ✅ Yes (line 105) |
| `SAAA_TIPO_ARCHIVO_ID` | Storage service | ✅ Yes (line 106) |
| `SAAA_TIMEOUT` | Storage service | ✅ Yes (line 107) |
| `SAAA_USE_FAKE` | `abstract_storage.py`, `di.py` | ❌ Not documented (commented out) |
| `CORS_ALLOW_ALL_ORIGINS` | Django CORS | ✅ Yes (line 131) |
| `CORS_ALLOWED_ORIGINS` | Django CORS | ✅ Yes (commented example line 132) |
| `CSRF_TRUSTED_ORIGINS` | Django CSRF | ✅ Yes (line 135) |

**Orphan env var in code**: None found. All code-read env vars are either in `.env.example` or (for `SAAA_USE_FAKE`) commented out.

---

### Verification Commands to Run

```bash
# 1. Verify MEDIA_URL in running backend container
docker-compose exec backend python -c "from django.conf import settings; print(settings.MEDIA_URL)"

# 2. Test media URL routing through proxy (when proxy is running)
curl -I http://localhost:7000/backend/media/test.png   # Should return 404 or proxy to backend

# 3. Test direct media routing
curl -I http://localhost:7000/media/test.png            # Should proxy to backend

# 4. Check nginx location matching for /backend/media/
# nginx -T to dump config and search for location blocks

# 5. Verify no hardcoded 10.10.5.177 references remain
rg "10\.10\.5\.177" --type py --type ts --type yaml

# 6. Verify BACKEND_API_URL is set in Docker frontend service
docker-compose exec frontend env | grep BACKEND_API_URL
```

---

### Recommendation

**Priority 1 — Fix the media routing chain**:
Either (A) add nginx `location /backend/media/` that proxies to `backend_upstream` without path rewriting, OR (B) revert `resolveImageUrl` to NOT prefix `/backend` for media paths and fix `MEDIA_URL` in docker-compose to an absolute Docker-internal URL (`http://backend:8000/media/`).

**Priority 2 — Fix docker-compose.yml `MEDIA_URL` hardcoded fallback**: Change line 67 from `http://10.10.5.177:12001/media/` to `http://backend:8000/media/`.

**Priority 3 — Document missing env vars**: Add `SAAA_USE_FAKE` to `.env.example` and add `BACKEND_API_URL` and `MEDIA_URL` to the backend server-side section.

**Priority 4 — Clean up `ws-probe.ts`**: Update `WS_URL` fallback to `ws://localhost:7000/ws/notificaciones/` and derive cookie name from `AUTH_STORAGE_PREFIX`.

**Note on `CORS_ALLOW_ALL_ORIGINS=True`**: Current default allows all origins. With proxy on port 7000, browser origin is `http://localhost:7000`. This is acceptable for dev but `CORS_ALLOWED_ORIGINS` should be explicitly set for production.
