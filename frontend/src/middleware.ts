import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const ADMIN_PREFIXES = ["/admin"];
const PROTECTED_PREFIXES = ["/module", "/patienten", "/settings", "/admin", "/berichte"];

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  const isProtected = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));
  if (!isProtected) return NextResponse.next();

  const role = request.cookies.get("user_role")?.value;

  if (!role) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  const isAdmin = ADMIN_PREFIXES.some((p) => pathname.startsWith(p));
  if (isAdmin && role !== "admin") {
    return NextResponse.redirect(new URL("/module/report", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/module/:path*",
    "/patienten/:path*",
    "/settings/:path*",
    "/admin/:path*",
    "/berichte/:path*",
  ],
};
