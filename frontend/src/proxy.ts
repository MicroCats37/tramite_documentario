import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { AUTH_COOKIES } from "@/lib/auth/cookies";

export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get(AUTH_COOKIES.ACCESS_TOKEN)?.value;

  // Auth page redirect (already logged in → app)
  if (pathname === "/login" && token) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  // Redirect to login if no token and trying to access protected area
  if (!token && !pathname.startsWith("/login")) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Excluir /backend/* (rewrites a Django) y /api/* (Next.js server routes)
  // para que el middleware no las redirija a /login.
  matcher: ["/((?!api|_next/static|_next/image|images|favicon.ico|backend).*)"],
};
