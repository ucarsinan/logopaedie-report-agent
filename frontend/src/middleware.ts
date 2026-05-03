import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_PATHS = [
  "/login",
  "/register",
  "/verify-email",
  "/forgot-password",
  "/reset-password",
];

const DEMO_ALLOWED_PATHS = ["/module/report", "/module/soap"];

function isPublic(pathname: string): boolean {
  return PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/"),
  );
}

function isAdmin(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

function isDemoAllowed(pathname: string): boolean {
  return DEMO_ALLOWED_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/"),
  );
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
    const isDemo =
      req.nextUrl.searchParams.get("demo") === "true" ||
      req.cookies.get("demo_mode")?.value === "true";

    if (isDemo && isDemoAllowed(pathname)) {
      const response = NextResponse.next();
      response.cookies.set("demo_mode", "true", {
        maxAge: 3600,
        path: "/",
        sameSite: "lax",
      });
      return response;
    }

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
