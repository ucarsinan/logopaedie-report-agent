import { NextResponse } from "next/server";
import {
  AUTH_REFRESH_PATH,
  backendTarget,
} from "../../_lib/backend-proxy";

const IS_PROD = process.env.NODE_ENV === "production";

export async function POST(req: Request): Promise<Response> {
  const cookieHeader = req.headers.get("cookie") ?? "";
  await fetch(backendTarget(req, "/auth/logout"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      cookie: cookieHeader,
    },
    body: JSON.stringify({}),
  }).catch(() => null);

  const res = NextResponse.json({ ok: true });
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
