import { NextResponse } from "next/server";

const DEFAULT_BACKEND_URL = "http://localhost:8001";

export const AUTH_REFRESH_PATH = "/auth-api/refresh";

export function backendTarget(req: Request, path: string): string {
  const rawBase =
    process.env.BACKEND_URL ??
    process.env.NEXT_PUBLIC_BACKEND_URL ??
    DEFAULT_BACKEND_URL;
  const base = rawBase.replace(/\/+$/, "");

  if (base.startsWith("/")) {
    return `${new URL(req.url).origin}${base}${path}`;
  }

  return `${base}${path}`;
}

export function readCookie(header: string | null, name: string): string | null {
  if (!header) return null;
  const match = header.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function jsonResponse(
  body: string,
  status: number,
): NextResponse {
  return new NextResponse(body, {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function responseHeaders(upstream: Response): Headers {
  const headers = new Headers();
  const contentType = upstream.headers.get("content-type");
  const contentDisposition = upstream.headers.get("content-disposition");

  if (contentType) headers.set("Content-Type", contentType);
  if (contentDisposition) {
    headers.set("Content-Disposition", contentDisposition);
  }

  return headers;
}
