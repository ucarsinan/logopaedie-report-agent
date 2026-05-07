import { NextResponse } from "next/server";
import {
  backendTarget,
  readCookie,
  responseHeaders,
} from "../../_lib/backend-proxy";

async function forward(
  req: Request,
  ctx: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await ctx.params;
  const url = new URL(req.url);
  const target = backendTarget(req, `/${path.join("/")}${url.search}`);
  const access = readCookie(req.headers.get("cookie"), "access_token");

  const headers = new Headers();
  const contentType = req.headers.get("content-type");
  const accept = req.headers.get("accept");

  if (contentType) headers.set("Content-Type", contentType);
  if (accept) headers.set("Accept", accept);
  if (access) headers.set("Authorization", `Bearer ${access}`);

  const init: RequestInit = {
    method: req.method,
    headers,
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  try {
    const upstream = await fetch(target, init);
    const body = await upstream.arrayBuffer();
    return new NextResponse(body, {
      status: upstream.status,
      headers: responseHeaders(upstream),
    });
  } catch {
    return new NextResponse(
      JSON.stringify({ detail: "service_unavailable" }),
      { status: 503, headers: { "Content-Type": "application/json" } },
    );
  }
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const DELETE = forward;
export const PATCH = forward;
