# Layout y Navegación del Dashboard

## Arquitectura del Layout

El layout del dashboard se compone en dos capas:

```
DashboardLayout (Server Component)
    └── DashboardShell (Client Component)
            ├── Sidebar
            ├── Header
            └── <main> (children)
```

### DashboardLayout (`src/app/dashboard/layout.tsx`)

Componente **Server** que actúa como guardián de autenticación:

```tsx
export default async function DashboardLayout({ children }) {
  const user = await getUserCookie(); // Cookie — validación server-side
  if (!user) redirect("/login");
  return <DashboardShell user={user}>{children}</DashboardShell>;
}
```

- Extrae el usuario de la cookie de autenticación
- Si no hay usuario → redirige a `/login`
- Si hay usuario válido → renderiza `DashboardShell` pasándole el usuario

### DashboardShell (`src/app/dashboard/components/DashboardShell.tsx`)

Contenedor **Client** que orquesta los componentes de navegación y consume el hook `useMisPendientes` para obtener el conteo de solicitudes pendientes:

```tsx
export function DashboardShell({ user, children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { data } = useMisPendientes();

  const totalSolicitudes =
    (data?.solicitud_asignado.cantidad || 0) +
    (data?.solicitudes_adjuntadas.cantidad || 0);

  return (
    <div className="flex h-screen">
      <Sidebar
        open={sidebarOpen}
        onToggle={setSidebarOpen}
        user={user}
        solicitudesCount={totalSolicitudes}
      />
      <div className="flex-1 flex flex-col">
        <Header sidebarOpen={sidebarOpen} onToggleSidebar={...} user={user} />
        <main>{children}</main>
      </div>
    </div>
  );
}
```

Puntos clave:
- **Estado del sidebar**: controlado localmente con `useState(false)` — cerrado por defecto en móvil
- **Consumo de datos**: llama `useMisPendientes` una sola vez y pasa el total al Sidebar
- **Layout responsive**: flexbox con `overflow-hidden` para evitar scroll en el contenedor padre

---

## Sidebar (`src/components/dashboard/sidebar.tsx`)

### Estructura visual

```
┌─────────────────────────┐
│  LOGO CIP               │
│  Mesa de Partes Virtual │
├─────────────────────────┤
│  ┌───────────────────┐  │
│  │ Avatar  Nombre    │  │ ← User Card
│  │        @username  │  │
│  │  Rol: [Admin]     │  │
│  └───────────────────┘  │
├─────────────────────────┤
│  MENÚ PRINCIPAL        │
│  ┌───────────────────┐  │
│  │ 🏠 Inicio         │  │ ← Link activo
│  └───────────────────┘  │
│  ┌───────────────────┐  │
│  │ 📥 Solicitudes [3]│  │ ← Badge dinámico
│  └───────────────────┘  │
│  ┌───────────────────┐  │
│  │ 📄 Expedientes    │  │
│  └───────────────────┘  │
├─────────────────────────┤
│  Configuración          │ ← Menú inferior
│  Ayuda                  │
│  Cerrar Sesión          │
└─────────────────────────┘
```

### Detección de Ruta Activa

El Sidebar usa `usePathname()` de Next.js para determinar qué enlace está activo:

```tsx
const pathname = usePathname();

const isActive =
  pathname === item.href ||
  (item.href !== "/dashboard" && pathname.startsWith(item.href));
```

Lógica:
- **`/`**: coincidencia exacta (`pathname === item.href`)
- **`/solicitudes` y `/expedientes`**: coincidencia por prefijo (`pathname.startsWith(item.href)`) — importante para sub-rutas como `/solicitudes/[id]`
- La excepción para `/dashboard` evita que "Inicio" esté siempre activo cuando se navega a sub-rutas

### Renderizado de Badges de Pendientes

El badge se renderiza en el menú "Solicitudes" cuando hay solicitudes pendientes:

```tsx
const menuItems = useMemo(() => [
  { name: "Inicio", href: "/dashboard", icon: Home },
  {
    name: "Solicitudes",
    href: "/dashboard/solicitudes",
    icon: Inbox,
    badge: solicitudesCount > 0 ? solicitudesCount.toString() : undefined,
  },
  { name: "Expedientes", href: "/dashboard/expedientes", icon: FileText },
], [solicitudesCount]);
```

```tsx
{item.badge && (
  <Badge className="bg-amber-500 text-amber-950 hover:bg-amber-400 text-xs px-2 py-0.5">
    {item.badge}
  </Badge>
)}
```

- El `useMemo` recalcula el array solo cuando cambia `solicitudesCount` — evita re-renderizados innecesarios
- El badge muestra el número en color ámbar cuando `solicitudesCount > 0`
- El valor viene de `DashboardShell`, que a su vez lo calcula desde `useMisPendientes`

### Menú Inferior y Logout

```tsx
const handleLogout = async () => {
  auth_clearSession();
  me_clearDetails();
  await logoutAction();
};
```

- Limpia el estado de autenticación del store (`auth_clearSession`, `me_clearDetails`)
- Ejecuta `logoutAction` en el servidor
- El menú inferior incluye Configuración, Ayuda y Cerrar Sesión

---

## Header (`src/components/dashboard/header.tsx`)

### Estructura visual

```
┌──────────────────────────────────────────────────────────┐
│ [☰]  Buenos días, Juan Pérez          [🔔 Notif] [👤 ▾] │
│       Panel de Usuario                                  │
└──────────────────────────────────────────────────────────┘
```

### Lado Izquierdo

- **Botón hamburger**: visible solo en móvil (`lg:hidden`), toggla el sidebar
- **Saludo dinámico**: basado en la hora del día ("Buenos días", "Buenas tardes", "Buenas noches")
- **Nombre del usuario**: `{user.fullname || user.username}`

### Lado Derecho

#### Dropdown de Notificaciones

```tsx
<DropdownMenu>
  <DropdownMenuTrigger>
    <Button variant="ghost" size="icon" className="relative">
      <Bell className="w-5 h-5" />
      <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary rounded-full animate-pulse" />
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent className="w-80">
    <DropdownMenuLabel>Notificaciones</DropdownMenuLabel>
    ...
  </DropdownMenuContent>
</DropdownMenu>
```

- Indicador pulsante rojo cuando hay notificaciones
- Muestra 3 notificaciones de ejemplo con tipo, expediente y tiempo
- En un futuro se conectará a una API real de notificaciones

#### Menú de Usuario

```tsx
<DropdownMenu>
  <DropdownMenuTrigger>
    <Button>
      <Avatar />
      <div className="hidden md:flex flex-col">
        <span>{user.username}</span>
        <span>{user.rol}</span>
      </div>
      <ChevronDown />
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent>
    <DropdownMenuLabel>
      {user.fullname || user.username}
      {user.email}
    </DropdownMenuLabel>
    <DropdownMenuItem>Mi Perfil</DropdownMenuItem>
    <DropdownMenuItem>Configuración</DropdownMenuItem>
    <DropdownMenuSeparator />
    <DropdownMenuItem className="text-destructive">Cerrar Sesión</DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

- Muestra avatar con iniciales, nombre de usuario y rol
- Menú desplegable con: Mi Perfil, Configuración, Cerrar Sesión
- El email se muestra en `DropdownMenuLabel` por ser la opción más compacta

---

## Flujo de Datos para el Badge de Pendientes

```
┌─────────────────────────────────────────────────────────────┐
│                        FLUJO                                │
│                                                             │
│  1. DashboardShell se monta                                 │
│         ↓                                                  │
│  2. useMisPendientes() → GET /api/pendientes/              │
│         ↓                                                  │
│  3. Server responde:                                       │
│     {                                                       │
│       solicitud_asignado: { cantidad: 2, detalle: [...] },  │
│       solicitudes_adjuntadas: { cantidad: 1, detalle: [...] }│
│     }                                                       │
│         ↓                                                  │
│  4. totalSolicitudes = 2 + 1 = 3                           │
│         ↓                                                  │
│  5. <Sidebar solicitudesCount={3} />                        │
│         ↓                                                  │
│  6. menuItems se recalcula (useMemo)                       │
│         ↓                                                  │
│  7. Badge ámbar "3" aparece junto a "Solicitudes"          │
└─────────────────────────────────────────────────────────────┘
```

Este flujo garantiza que:
- Los datos se cargan una sola vez en el Shell (no duplicación)
- El sidebar siempre muestra el conteo actualizado
- No hay llamada adicional desde el Sidebar para el conteo
