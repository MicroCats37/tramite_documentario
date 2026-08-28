# Flujo de Autenticación — Login y Sesión

## Índice

1. [Arquitectura General](#1-arquitectura-general)
2. [Middleware: Protección de Rutas](#2-middleware-protección-de-rutas)
3. [Dos Implementaciones de Login](#3-dos-implementaciones-de-login)
4. [Gestión de Cookies y Sesión](#4-gestión-de-cookies-y-sesión)
5. [Store de Estado (Zustand)](#5-store-de-estado-zustand)
6. [Esquemas Zod](#6-esquemas-zod)
7. [Flujo Completo Paso a Paso](#7-flujo-completo-paso-a-paso)
8. [Hallazgos Técnicos](#8-hallazgos-técnicos)

---

## 1. Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│                        NAVEGADOR                                 │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ LoginPage │───▶│ LoginForm    │───▶│ useLogin hook    │   │
│  │ /login    │    │ (React Query)│    │ (useApiCreate)   │   │
│  └──────────┘    └──────────────┘    └────────┬─────────┘   │
│                                                │              │
│  ┌──────────┐    ┌──────────────┐    ┌────────▼─────────┐   │
│  │ Dashboard│◀───│ middleware.ts│◀───│ Cookie: jwt-token│   │
│  │ /dashboard│    │ (Next.js)    │    │ (httpOnly:false)│   │
│  └──────────┘    └──────────────┘    └─────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Zustand Store (sessionStorage)              │  │
│  │  auth_user | auth_accessToken | auth_refreshToken         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (Django)                            │
│                    localhost:8000                                │
│                                                                 │
│   POST /api/login/  → { access, refresh, user }                │
│   POST /api/token/refresh/ → { access }                        │
│   POST /api/logout/                                             │
└─────────────────────────────────────────────────────────────────┘
```

### Rutas Públicas vs Protegidas

| Ruta | Protección | Notas |
|------|------------|-------|
| `/login` | Pública | Solo accesible si NO hay sesión válida |
| `/` | Pública | Landing page |
| `/dashboard` | Requiere JWT válido | Redirige a `/login` si no hay token |
| `/api/*` | Excluida | El matcher del middleware las ignora |

---

## 2. Middleware: Protección de Rutas

**Archivo:** `src/middleware.ts`

```typescript
const PUBLIC_PATHS = ["/login", "/"];

export function middleware(request: NextRequest) {
  const token = request.cookies.get("jwt-token")?.value;
  const path = request.nextUrl.pathname;
  const isPublicPath = PUBLIC_PATHS.includes(path);

  // Caso 1: Sin token
  if (!token) {
    if (!isPublicPath) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
    return NextResponse.next();
  }

  // Caso 2: Token presente → verificar expiración
  const decoded = decodeJWT(token);
  const now = Math.floor(Date.now() / 1000);

  if (!decoded || decoded.exp < now) {
    const res = NextResponse.redirect(new URL("/login", request.url));
    res.cookies.set("jwt-token", "", { expires: new Date(0) });
    return res;
  }

  // Caso 3: Token válido + intenta acceder a /login → redirigir a dashboard
  if (path === "/login") {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
```

### Cómo funciona la validación JWT

1. **Extracción**: Lee la cookie `jwt-token` directamente de la request
2. **Decodificación**: Divide el JWT en sus 3 partes (header.payload.signature) y hace `atob()` del payload
3. **Verificación de expiración**: Compara `decoded.exp` con el timestamp actual en segundos
4. **Limitación importante**: El middleware NO valida la firma del JWT — solo decodifica y verifica expiración. La validación real de firma ocurre en el backend Django.

### Matcher y rutas excluidas

El matcher `"/((?!api|_next/static|_next/image|favicon.ico).*)"` excluye:
- `/api/*` — Rutas de API de Next.js (no son el backend Django)
- `/_next/static/*` — Assets estáticos de Next.js
- `/_next/image/*` — Optimización de imágenes
- `/favicon.ico` — Ícono

---

## 3. Dos Implementaciones de Login

### Hallazgo: Convivencia de dos enfoques

Existen **dos implementaciones de LoginForm** en el codebase que usan paradigmas completamente diferentes:

#### Implementación A: Server Actions (Usada activamente en `page.tsx`)

**Archivo:** `src/components/auth/loginform.tsx`

```typescript
"use client";

import { useTransition } from "react";
import { loginAction } from "@/actions/auth"; // Server Action

export function LoginForm() {
  const [isPending, startTransition] = useTransition();

  const onSubmit = (values) => {
    startTransition(async () => {
      const result = await loginAction(values);
      if (result?.error) {
        setError(result.error);
      }
      // Si tiene éxito, loginAction llama a redirect('/dashboard')
    });
  };
}
```

**Server Action** (`src/actions/auth.ts`):

```typescript
"use server";

export async function loginAction(formData: LoginFormDataType) {
  // 1. Validación Zod de entrada
  const validatedFields = LoginFormDataSchema.safeParse(formData);
  if (!validatedFields.success) {
    return { error: `Datos inválidos: ${formattedErrors}` };
  }

  // 2. Llamada HTTP al backend Django
  try {
    const { access, refresh, user } = await callLoginAPI(validatedFields.data);
  } catch (error) {
    return { error: error.message };
  }

  // 3. Guardar cookies en el servidor
  await setAuthCookie(accessToken, refreshToken, userLogin);

  // 4. REDIRECCIÓN: Next.js maneja la navegación
  redirect("/dashboard");
}
```

**Flujo:**
1. Formulario → `loginAction` (Server Action)
2. `loginAction` valida con Zod → llama al backend → guarda cookies → `redirect("/dashboard")`
3. El `redirect()` de Next.js causa una navegación full-page

#### Implementación B: React Query (En desuso o alternativa)

**Archivo:** `src/app/(auth)/login/components/LoginForm.tsx`

```typescript
"use client";

import { useLogin } from "../_hooks/useAuth"; // Hook React Query

export function LoginForm() {
  const { mutate: login, isPending, error } = useLogin();

  const onSubmit = (values) => {
    login(values); // No necesita startTransition
  };
}
```

**Hook** (`src/app/(auth)/login/_hooks/useAuth.ts`):

```typescript
export const useLogin = () => {
  return useApiCreate<LoginResponseType, LoginFormDataType>({
    url: `${API_URL}/api/login/`,
    schema: LoginResponseSchema,
    options: {
      onSuccess: async (data) => {
        await setAuthCookie(access, refresh, user); // "use server" function
        router.push("/dashboard"); // Navegación client-side
        router.refresh();
      },
    },
  });
};
```

**Flujo:**
1. Formulario → `useLogin.mutate()` (React Query mutation)
2. `useApiCreate` hace el POST HTTP
3. `onSuccess`: llama a `setAuthCookie` (Server Action via `"use server"`) → `router.push()` (client-side)

### Comparación

| Aspecto | Server Actions | React Query |
|---------|---------------|-------------|
| Paradigma | Form submit server-side | Mutación async client-side |
| Navegación post-login | `redirect()` full-page | `router.push()` client-side |
| Manejo de errores | Return object `{ error }` | `onError` callback |
| Estados de carga | `useTransition` | `isPending` de React Query |
| Validación | Zod en servidor | Zod en cliente + servidor |
| Retry automático | No | Sí (configurable) |
| Cache invalidation | Manual | Automático |

### ¿Cuál se usa?

El `page.tsx` de login importa `src/components/auth/loginform.tsx` (Server Actions). La otra implementación en `src/app/(auth)/login/components/LoginForm.tsx` parece ser una alternativa en paralelo o código de migración.

---

## 4. Gestión de Cookies y Sesión

**Archivo:** `src/lib/auth/utils.ts`

Todas las funciones en este archivo tienen la directiva `"use server"`, lo que significa que solo pueden ejecutarse en el servidor (Server Components, Server Actions).

### Cookies establecidas tras login

```typescript
await setAuthCookie(accessToken, refreshToken, userLogin);
```

| Cookie | Nombre | HttpOnly | Max-Age | Valor |
|--------|--------|----------|---------|-------|
| Access Token | `jwt-token` | `false` ⚠️ | 5 min | JWT de acceso |
| Refresh Token | `jwt-refresh-token` | `false` ⚠️ | 1 semana | JWT de refresh |
| User Data | `user-login` | `false` ⚠️ | 1 semana | JSON con datos de usuario |

### ⚠️ Hallazgo de seguridad

**Todas las cookies tienen `httpOnly: false`**, lo que significa que JavaScript del cliente puede leerlas directamente:

```typescript
// Desde cualquier componente cliente:
document.cookie; // Contiene todas las cookies incluyendo jwt-token
```

Esto es una decisión de diseño deliberada (el middleware también necesita leer el JWT para verificar expiración). Sin embargo:
- El token NO debe contener información sensible más allá de lo necesario para la expiración
- La firma del JWT se valida en el backend, no en el frontend
- Para mayor seguridad, considerar cookies `httpOnly: true` y un endpoint `/api/me` que el cliente consulte

### Obtención de cookies (Server)

```typescript
// En contexto server (Server Components, Server Actions)
const token = (await cookies()).get("jwt-token")?.value;
```

### Eliminación de cookies

```typescript
await deleteAllAuthCookies();
// Equivalente a:
cookies().delete("jwt-token");
cookies().delete("jwt-refresh-token");
cookies().delete("user-login");
```

### Refresh automático de token

```typescript
export async function refreshAuthToken(): Promise<boolean> {
  const refreshToken = await getRefreshToken();
  const response = await fetch(`${API_URL}/api/token/refresh/`, {
    method: "POST",
    body: JSON.stringify({ refresh: refreshToken }),
  });
  // Si exitoso, guarda el nuevo access token
  await setAuthCookie(data.access, data.refresh || refreshToken, data.user || await getUserCookie());
  return true;
}
```

### Fetch autenticado con auto-refresh

```typescript
export async function authFetch(url, options = {}) {
  let token = await getAuthToken();
  let response = await makeRequest(token);

  // Si el backend devuelve 401, intentar refresh
  if (response.status === 401) {
    const refreshSuccess = await refreshAuthToken();
    if (refreshSuccess) {
      token = await getAuthToken();
      response = await makeRequest(token);
    } else {
      throw new Error("SESSION_EXPIRED");
    }
  }
  return response;
}
```

---

## 5. Store de Estado (Zustand)

**Archivo:** `src/store/authStorage.ts`

### Estructura del Store

```typescript
export const useAppStore = create<AppStore>()(
  persist(
    (set, get, store) => ({
      ...createAuthSlice(set, get, store),
      ...createMeSlice(set, get, store),
    }),
    {
      name: "app-auth-storage",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        auth_user: state.auth_user,
        auth_accessToken: state.auth_accessToken,
        auth_refreshToken: state.auth_refreshToken,
      }),
    },
  ),
);
```

### Slice de Autenticación (AuthSlice)

```typescript
interface AuthSliceState {
  auth_user: LoginUserData | null;
  auth_accessToken: string | null;
  auth_refreshToken: string | null;
}

interface AuthSliceActions {
  auth_setSession: (session: { user: LoginUserData; access: string; refresh: string }) => void;
  auth_clearSession: () => void;
}
```

### Slice de Perfil (MeSlice)

```typescript
interface MeSliceState {
  me_details: UserDataMe | null;
}

interface MeSliceActions {
  me_setUserDetails: (data: UserDataMe) => void;
  me_clearDetails: () => void;
}
```

### Persistencia

- **Storage**: `sessionStorage` (no `localStorage`)
- **Key**: `app-auth-storage`
- **Partialize**: Solo persiste datos de autenticación, NO los detalles del perfil

### ⚠️ Hallazgo: Store desconectado del flujo de login

El store **NO se usa activamente** en el flujo de login actual:

1. La implementación Server Action (`src/components/auth/loginform.tsx`) tiene la línea comentada:
   ```typescript
   // const auth_setSession = useAppStore(state => state.auth_setSession);
   ```

2. La implementación React Query (`useLogin`) tampoco lo usa directamente

3. El store persiste tokens en `sessionStorage`, pero las cookies ya contienen esta información

**Esto sugiere** que el store podría estar pensado para:
- Sincronizar estado entre pestañas
- Mantener datos de sesión entre recargas sin consultar cookies
- Uso futuro en componentes que requieran acceso directo al token

---

## 6. Esquemas Zod

**Archivo:** `src/schemas/auth/index.ts`

### Login

```typescript
// Datos del formulario
export const LoginFormDataSchema = z.object({
  username: z.string(),
  password: z.string(),
});

// Respuesta del backend
export const LoginResponseSchema = z.object({
  refresh: z.string(),
  access: z.string(),
  user: LoginResponseUserSchema,
});

// Datos del usuario
export const LoginResponseUserSchema = z.object({
  user_id: z.number(),
  username: z.string(),
  fullname: z.string(),
  rol: z.string(),
  email: z.email(),
  is_superuser: z.boolean().optional(),
});
```

### Usuario y Perfil

```typescript
export const UserSchema = z.object({
  id: z.number(),
  username: z.string(),
  fullname: z.string(),
  email: z.string(),
  rol: z.string().nullable().optional(),
  perfil: UserPerfilSchema.nullable().optional(),
  permisos: z.array(z.string()),
});
```

---

## 7. Flujo Completo Paso a Paso

### Login (Server Actions)

```
1. Usuario llena formulario en /login
                    │
                    ▼
2. onSubmit() → startTransition(() => loginAction(values))
                    │
                    ▼
3. loginAction (Server Action):
   a. LoginFormDataSchema.safeParse(values) → valida entrada
   b. Si falla → return { error: "..." }
   c. Si pasa → callLoginAPI({ username, password })
                    │
                    ▼
4. fetch("http://localhost:8000/api/login/", {
     method: "POST",
     body: JSON.stringify({ username, password })
   })
                    │
                    ▼
5. Backend Django devuelve:
   { access: "eyJ...", refresh: "eyJ...", user: { user_id, username, fullname, ... } }
                    │
                    ▼
6. LoginResponseSchema.safeParse(responseJson) → valida respuesta
                    │
                    ▼
7. setAuthCookie(access, refresh, user) → guarda 3 cookies
                    │
                    ▼
8. redirect("/dashboard") → navegación full-page
```

### Acceso a ruta protegida

```
1. Usuario accede a /dashboard
                    │
                    ▼
2. middleware.ts ejecuta:
   a. token = cookies.get("jwt-token")?.value
   b. decoded = decodeJWT(token) // { exp: 1234567890, ... }
   c. now = Math.floor(Date.now() / 1000)
   d. decoded.exp < now ? → token expirado → redirect /login
                    │
                    ▼
3. Token válido y no expirado → NextResponse.next()
                    │
                    ▼
4. /dashboard renderiza, puede leer cookies o llamar authFetch()
```

### Refresh de token

```
1. authFetch() recibe 401 del backend
                    │
                    ▼
2. refreshAuthToken():
   a. getRefreshToken() → lee cookie jwt-refresh-token
   b. fetch("/api/token/refresh/", { method: "POST", body: { refresh } })
   c. Backend devuelve { access: "nuevo_token" }
   d. setAuthCookie(nuevo_access, refresh_existente, user_existente)
                    │
                    ▼
3. Reintentar request original con nuevo access token
```

### Logout

```
1. logoutAction() (Server Action):
   a. deleteAllAuthCookies() → elimina las 3 cookies
   b. redirect("/login")
```

---

## 8. Hallazgos Técnicos

### 8.1 Dos implementaciones de login en paralelo

Existen dos `LoginForm` con paradigmas diferentes:
- `src/components/auth/loginform.tsx` — Server Actions (la que se importa en `page.tsx`)
- `src/app/(auth)/login/components/LoginForm.tsx` — React Query (hook `useLogin`)

El `page.tsx` actual usa la versión Server Actions. La versión React Query parece ser una implementación alternativa o en proceso de migración.

### 8.2 Cookies sin HttpOnly

Todas las cookies de autenticación tienen `httpOnly: false`, permitiendo lectura desde JavaScript cliente. Esto es necesario porque:
- El middleware necesita leer el JWT para verificar expiración
- No hay endpoint `/api/me` que el cliente pueda consultar

**Tradeoff**: Si hay XSS, las cookies pueden ser robadas. Mitigación: el token de acceso expira en 5 minutos.

### 8.3 Store de Zustand no utilizado en login

El store `useAppStore` con persistencia en `sessionStorage` está definido pero no se usa activamente en el flujo de login actual. Los tokens se guardan en cookies HTTP, no en el store.

### 8.4 Duraciones de cookies

| Cookie | TTL | Justificación |
|--------|-----|---------------|
| `jwt-token` | 5 minutos | Token de acceso corto — minimiza ventana de exposición |
| `jwt-refresh-token` | 1 semana | Permite refresh sin re-login frecuente |
| `user-login` | 1 semana | Datos de usuario para UI sin llamada extra |

### 8.5 Sin validación de firma en middleware

El middleware solo decodifica y verifica expiración del JWT. La validación de firma (contra la clave secreta del backend Django) ocurre solo cuando el backend recibe el token. Esto es aceptable porque:
- El middleware es solo para UX (redirect a login)
- El backend siempre valida la firma en cada request protegido

### 8.6 API URL configurada via entorno

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

Todas las llamadas HTTP van al backend Django. El frontend Next.js actúa solo como proxy/ cliente.

---

## Archivos del lote

```
frontend/src/
├── middleware.ts                          # Protección de rutas + validación JWT
├── actions/auth.ts                       # Server Action: login + logout
├── app/(auth)/login/
│   ├── page.tsx                          # Página de login (usa LoginForm de components)
│   ├── components/LoginForm.tsx           # Login con React Query (alternativa)
│   └── _hooks/useAuth.ts                 # Hook useLogin (React Query)
├── components/auth/loginform.tsx          # Login con Server Actions (en uso)
├── lib/auth/
│   ├── utils.ts                          # "use server": cookies, refresh, authFetch
│   ├── fetchAuth.ts                      # FetchClient class (duplicado de utils?)
│   └── client-utils.ts                    # Utils cliente para cookies
├── schemas/auth/index.ts                 # Zod schemas para auth
├── store/authStorage.ts                  # Zustand store (persistencia sessionStorage)
└── hooks/useApiCreate.tsx                # Hook genérico React Query mutations
```
