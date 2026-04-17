import { NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8001";
const IS_PROD = process.env.NODE_ENV === "production";

export async function POST(req: Request): Promise<Response> {
  const cookieHeader = req.headers.get("cookie") ?? "";
  await fetch(`${BACKEND}/auth/logout`, {
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
  // refresh_token is scoped to /api/auth/refresh — clear with matching path
  res.cookies.set("refresh_token", "", { ...clearOpts, path: "/api/auth/refresh" });
  res.cookies.set("user_role", "", {
    httpOnly: false,
    secure: IS_PROD,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  return res;
}
