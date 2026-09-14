"use client";

import {
  BookOpen,
  FolderSearch,
  Inbox,
  LogOutIcon,
  Menu,
  User,
  X,
} from "lucide-react";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { MeResponse } from "@/features/auth/schemas/auth.types";
import { useAuthStore } from "@/features/auth/store/auth.store";
import { useIsMobile } from "@/hooks/use-mobile";
import { cn } from "@/lib/utils";

/**
 * Top-level nav items replacing the old mesaDePartesGroup accordion.
 */
const navItems = [
  {
    title: "Expedientes",
    href: "/expedientes",
    icon: FolderSearch,
  },
  {
    title: "Solicitudes",
    href: "/solicitudes",
    icon: Inbox,
  },
  {
    title: "Libro de Reclamaciones",
    href: "/libro-reclamaciones",
    icon: BookOpen,
  },
];

/**
 * ProtectedSidebar — elegant institutional sidebar matching the login aesthetic.
 * Wine red + gold corporate theme, refined spacing, subtle micro-interactions.
 * Supports desktop collapse/expand via controlled `collapsed` + `onCollapsedChange` props.
 */
export function ProtectedSidebar({
  user,
  collapsed: controlledCollapsed,
  onCollapsedChange,
}: {
  user: MeResponse;
  collapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useAuthStore((state) => state.logout);
  const isMobile = useIsMobile();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [internalCollapsed, setInternalCollapsed] = useState(false);

  // Controlled or uncontrolled collapsed state
  const collapsed = controlledCollapsed ?? internalCollapsed;
  const setCollapsed = (value: boolean) => {
    if (controlledCollapsed !== undefined) {
      onCollapsedChange?.(value);
    } else {
      setInternalCollapsed(value);
    }
  };

  const handleLogout = async () => {
    try {
      const { clearAuthCookies } = await import("@/lib/auth");
      await clearAuthCookies();
      logout();
      router.push("/login");
    } catch {
      // If clearAuthCookies fails, still logout locally
      logout();
      router.push("/login");
    }
  };

  const handleNavClick = () => {
    if (isMobile) {
      setMobileOpen(false);
    }
  };

  const handleToggleCollapse = () => {
    setCollapsed(!collapsed);
  };

  const sidebarContent = (
    <>
      {/* ─── Header: wine/gold gradient brand panel — CLICKABLE TOGGLE ─── */}
      <button
        type="button"
        onClick={handleToggleCollapse}
        className={cn(
          "relative flex cursor-pointer border-b border-white/10 bg-white/[0.04] hover:bg-white/[0.07] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50 focus-visible:ring-inset",
          collapsed
            ? "h-16 w-full items-center justify-center"
            : "items-center gap-3 px-5 py-5",
        )}
        title={collapsed ? "Expandir sidebar" : "Colapsar sidebar"}
        aria-label={collapsed ? "Expandir sidebar" : "Colapsar sidebar"}
      >
        {/* Logo mark — CIP logo in rounded container */}
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white shadow-lg shadow-black/20 ring-2 ring-white/30 overflow-hidden">
          <Image
            src="/images/logo.png"
            alt="CIP"
            width={42}
            height={42}
            className="h-10 w-10 object-contain"
          />
        </div>
        {/* Brand text — hidden when collapsed */}
        {!collapsed && (
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-sm font-black tracking-wide text-white">
              Mesa de Partes
            </span>
            <span className="truncate text-[10px] font-semibold uppercase tracking-widest text-white/70">
              Colegio de Ingenieros del Perú
            </span>
          </div>
        )}
      </button>

      {/* ─── Navigation ─── */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-4">
        {/* Section label — hidden when collapsed */}
        {!collapsed && (
          <p className="mb-3 px-2 text-[10px] font-black uppercase tracking-[0.22em] text-white/45">
            Navegación
          </p>
        )}

        {/* Top-level nav items */}
        <div className="space-y-0.5">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <a
                key={item.href}
                href={item.href}
                onClick={handleNavClick}
                className={cn(
                  "group/item relative flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-bold transition-all duration-200 ease-out",
                  isActive
                    ? "bg-white/15 text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]"
                    : "text-white/78 hover:bg-white/10 hover:text-white hover:translate-x-0.5",
                  collapsed && "w-full justify-center px-0",
                )}
                title={collapsed ? item.title : undefined}
              >
                {/* Wine/gold left-border active indicator */}
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-full bg-accent shadow-sm" />
                )}
                {/* Icon container */}
                <span
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-xl transition-all duration-200",
                    isActive
                      ? "bg-white text-primary shadow-sm"
                      : "bg-white/10 text-white/80 group-hover/item:bg-white/15 group-hover/item:text-white",
                  )}
                >
                  <item.icon className="h-3.5 w-3.5" />
                </span>
                {!collapsed && (
                  <span className="min-w-0 flex-1">{item.title}</span>
                )}
              </a>
            );
          })}
        </div>
      </nav>

      {/* ─── Subtle gold separator above footer ─── */}
      <div
        className="mx-4 mb-1 h-px bg-gradient-to-r from-transparent via-accent/60 to-transparent"
        aria-hidden="true"
      />

      {/* ─── Footer: user dropdown + logout ─── */}
      <div className="border-t border-white/10 px-3 py-3">
        {/* User dropdown — shadcn DropdownMenu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className={cn(
                "flex w-full items-center gap-3 rounded-2xl bg-white/8 px-3 py-3 backdrop-blur-sm transition-colors duration-200 hover:bg-white/12 cursor-pointer",
                collapsed && "w-full justify-center px-0",
              )}
              title={
                collapsed ? `${user.datos.nombres} ${user.datos.apellidos}` : undefined
              }
            >
              <Avatar size="sm" className="shrink-0 ring-2 ring-primary/20">
                <AvatarFallback className="bg-white text-primary text-xs font-bold">
                  {user.datos.nombres?.charAt(0) ?? ""}
                  {user.datos.apellidos?.charAt(0) ?? ""}
                </AvatarFallback>
              </Avatar>
              {!collapsed && (
                <div className="flex min-w-0 flex-col text-left">
                  <p className="truncate text-sm font-bold text-white">
                    {user.datos.nombres} {user.datos.apellidos}
                  </p>
                  <p className="truncate text-[10px] text-white/55">
                    Funcionario
                  </p>
                </div>
              )}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" sideOffset={8} className="w-52">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col gap-0.5">
                <p className="text-sm font-semibold">
                  {user.datos.nombres} {user.datos.apellidos}
                </p>
                <p className="text-xs text-muted-foreground">Funcionario</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="gap-2">
              <User className="h-4 w-4 text-muted-foreground" />
              <span>Perfil</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant="destructive"
              className="gap-2"
              onClick={handleLogout}
            >
              <LogOutIcon className="h-4 w-4" />
              <span>Cerrar sesión</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </>
  );

  // Mobile: floating toggle + overlay sidebar with backdrop
  if (isMobile) {
    return (
      <>
        {/* Floating menu button — matches institutional style */}
        {!mobileOpen && (
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="Abrir menú"
            className={cn(
              "fixed top-4 left-4 z-40 flex h-10 w-10 items-center justify-center rounded-xl",
              "bg-primary text-primary-foreground shadow-lg",
              "transition-all duration-200 ease-out hover:bg-primary/90 hover:scale-105 active:scale-95",
            )}
          >
            <Menu className="h-5 w-5" />
          </button>
        )}

        {/* Backdrop */}
        {mobileOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
        )}

        {/* Overlay sidebar */}
        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-[radial-gradient(circle_at_top_left,oklch(0.55_0.15_25),transparent_18rem),linear-gradient(180deg,oklch(0.38_0.16_22),oklch(0.25_0.12_24))] text-white shadow-2xl",
            "transform transition-transform duration-300 ease-out",
            mobileOpen ? "translate-x-0" : "-translate-x-full",
          )}
        >
          {/* Mobile close button */}
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            aria-label="Cerrar menú"
            className={cn(
              "absolute top-4 right-4 flex h-8 w-8 items-center justify-center rounded-lg",
              "text-muted-foreground transition-all duration-200",
              "hover:bg-sidebar-accent hover:text-sidebar-foreground active:scale-95",
            )}
          >
            <X className="h-5 w-5" />
          </button>

          {sidebarContent}
        </aside>
      </>
    );
  }

  // Desktop: elegant sidebar with subtle shadow and right border
  return (
    <aside
      className={cn(
        "flex h-svh flex-col bg-[radial-gradient(circle_at_top_left,oklch(0.55_0.15_25),transparent_18rem),linear-gradient(180deg,oklch(0.38_0.16_22),oklch(0.25_0.12_24))] text-white border-r border-primary/20 shadow-xl shadow-primary/10 transition-all duration-200",
        collapsed ? "w-[4.75rem]" : "w-64",
      )}
    >
      {sidebarContent}
    </aside>
  );
}
