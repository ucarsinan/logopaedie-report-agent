import { NextResponse } from "next/server";
import {
  AUTH_REFRESH_PATH,
  backendTarget,
  jsonResponse,
  readCookie,
} from "../../_lib/backend-proxy";

const IS_PROD = process.env.NODE_ENV === "production";
const ACCESS_MAX_AGE = 60 * 15;
const REFRESH_MAX_AGE = 60 * 60 * 24 * 7;

export async function POST(req: Request): Promise<Response> {
  const refresh = readCookie(req.headers.get("cookie"), "refresh_token");
  if (!refresh) {
    return jsonResponse(JSON.stringify({ detail: "no refresh token" }), 401);
  }

  let upstream: Response;
  try {
    upstream = await fetch(backendTarget(req, "/auth/refresh"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
  } catch {
    return jsonResponse(JSON.stringify({ detail: "service_unavailable" }), 503);
  }

  if (!upstream.ok) {
    return jsonResponse(await upstream.text(), upstream.status);
  }

  const payload = await upstream.json();
  const res = NextResponse.json({ ok: true });
  res.cookies.set("access_token", payload.access_token, {
    httpOnly: true,
    secure: IS_PROD,
    sameSite: "lax",
    path: "/",
    maxAge: ACCESS_MAX_AGE,
  });
  res.cookies.set("refresh_token", payload.refresh_token, {
    httpOnly: true,
    secure: IS_PROD,
    sameSite: "lax",
    path: AUTH_REFRESH_PATH,
    maxAge: REFRESH_MAX_AGE,
  });
  return res;
}
