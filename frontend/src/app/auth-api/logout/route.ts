import { NextResponse } from "next/server";
import {
  AUTH_REFRESH_PATH,
  backendTarget,
  readCookie,
} from "../../_lib/backend-proxy";

const IS_PROD = process.env.NODE_ENV === "production";

function clearCookies(res: NextResponse): NextResponse {
  const clearOpts = {
    httpOnly: true,
    secure: IS_PROD,
    sameSite: "lax" as const,
    path: "/",
    maxAge: 0,
  };
  res.cookies.set("access_token", "", clearOpts);
  res.cookies.set("refresh_token", "", { ...clearOpts, path: AUTH_REFRESH_PATH });
  res.cookies.set("user_role", "", {
    httpOnly: false,
    secure: IS_PROD,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  return res;
}

export async function POST(req: Request): Promise<Response> {
  const refresh = readCookie(req.headers.get("cookie"), "refresh_token");

  if (refresh) {
    try {
      const upstream = await fetch(backendTarget(req, "/auth/logout"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!upstream.ok && !IS_PROD) {
        console.warn(
          `[auth-api/logout] backend revocation failed: ${upstream.status}`,
        );
      }
    } catch (err) {
      if (!IS_PROD) {
        console.warn("[auth-api/logout] backend revocation threw", err);
      }
    }
  }

  return clearCookies(NextResponse.json({ ok: true }));
}
