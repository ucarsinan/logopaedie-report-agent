import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_PATHS = [
  "/login",
  "/register",
  "/verify-email",
  "/forgot-password",
  "/reset-password",
];

function isPublic(pathname: string): boolean {
  return PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/"),
  );
}

function isAdmin(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

export function middleware(req: NextRequest): NextResponse {
  const { pathname } = req.nextUrl;
  const access = req.cookies.get("access_token")?.value;
  const role = req.cookies.get("user_role")?.value;

  if (access && isPublic(pathname)) {
    return NextResponse.redirect(new URL("/", req.url));
  }

  if (isPublic(pathname)) {
    return NextResponse.next();
  }

  if (!access) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // NOTE: user_role cookie is a UI-only gate (not httpOnly, readable by JS).
  // Backend enforces real authorization on every request via Bearer token.
  // A tampered user_role=admin cookie only exposes the admin UI shell;
  // all data fetches will still fail at the backend with 403.
  if (isAdmin(pathname) && role !== "admin") {
    return NextResponse.redirect(new URL("/", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/).*)"],
};
