import { NextResponse, type NextRequest } from "next/server";

// Accessible without auth — no redirect away even when logged in
const OPEN_PATHS = ["/"];

// Redirect logged-in users away to / (login page shouldn't show when authenticated)
const AUTH_PAGES = [
  "/login",
  "/register",
  "/verify-email",
  "/forgot-password",
  "/reset-password",
];

const DEMO_ALLOWED_PATHS = ["/module/report", "/module/soap"];

function isOpen(pathname: string): boolean {
  return OPEN_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/"),
  );
}

function isAuthPage(pathname: string): boolean {
  return AUTH_PAGES.some(
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

export function proxy(req: NextRequest): NextResponse {
  const { pathname } = req.nextUrl;
  const access = req.cookies.get("access_token")?.value;
  const role = req.cookies.get("user_role")?.value;

  // Landing page and other open paths: always accessible
  if (isOpen(pathname)) {
    return NextResponse.next();
  }

  // Auth pages: redirect logged-in users back to app
  if (access && isAuthPage(pathname)) {
    return NextResponse.redirect(new URL("/module/report", req.url));
  }

  if (isAuthPage(pathname)) {
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
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|api/|auth-api/|backend-api/|_svc/).*)",
  ],
};
