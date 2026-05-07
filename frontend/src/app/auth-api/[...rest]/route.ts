import { NextResponse } from "next/server";
import {
  backendTarget,
  jsonResponse,
  readCookie,
} from "../../_lib/backend-proxy";

const ALLOWED_PREFIXES = [
  "/verify-email",
  "/resend-verification",
  "/password/",
  "/2fa/",
  "/sessions",
  "/totp/",
];

async function forward(
  req: Request,
  ctx: { params: Promise<{ rest: string[] }> },
): Promise<Response> {
  const { rest } = await ctx.params;
  const path = "/" + rest.join("/");

  if (!ALLOWED_PREFIXES.some((p) => path.startsWith(p))) {
    return jsonResponse(JSON.stringify({ detail: "not found" }), 404);
  }
  const url = new URL(req.url);
  const target = backendTarget(req, `/auth${path}${url.search}`);
  const access = readCookie(req.headers.get("cookie"), "access_token");

  const headers: Record<string, string> = {
    "Content-Type": req.headers.get("content-type") ?? "application/json",
  };
  if (access) headers.Authorization = `Bearer ${access}`;

  const init: RequestInit = { method: req.method, headers };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }

  try {
    const upstream = await fetch(target, init);
    return jsonResponse(await upstream.text(), upstream.status);
  } catch {
    return new NextResponse(JSON.stringify({ detail: "service_unavailable" }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });
  }
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const DELETE = forward;
export const PATCH = forward;
