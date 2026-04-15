import { NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8001";

// Only forward known safe paths — prevents accidental exposure of future
// privileged backend auth endpoints (e.g. /auth/users, /auth/admin/*).
const ALLOWED_PREFIXES = [
  "/verify-email",
  "/resend-verification",
  "/password/",
  "/totp/",
];

function readCookie(header: string | null, name: string): string | null {
  if (!header) return null;
  const match = header.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function forward(
  req: Request,
  ctx: { params: Promise<{ rest: string[] }> },
): Promise<Response> {
  const { rest } = await ctx.params;
  const path = "/" + rest.join("/");

  if (!ALLOWED_PREFIXES.some((p) => path.startsWith(p))) {
    return new Response(JSON.stringify({ detail: "not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  }
  const url = new URL(req.url);
  const target = `${BACKEND}/auth${path}${url.search}`;
  const access = readCookie(req.headers.get("cookie"), "access_token");

  const headers: Record<string, string> = {
    "Content-Type": req.headers.get("content-type") ?? "application/json",
  };
  if (access) headers.Authorization = `Bearer ${access}`;

  const init: RequestInit = { method: req.method, headers };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }

  const upstream = await fetch(target, init);
  return new NextResponse(await upstream.text(), {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const DELETE = forward;
export const PATCH = forward;
