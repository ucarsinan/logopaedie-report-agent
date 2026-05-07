import {
  backendTarget,
  jsonResponse,
  readCookie,
} from "../../_lib/backend-proxy";

export async function GET(req: Request): Promise<Response> {
  const access = readCookie(req.headers.get("cookie"), "access_token");
  if (!access) {
    return jsonResponse(JSON.stringify({ detail: "unauthenticated" }), 401);
  }
  try {
    const upstream = await fetch(backendTarget(req, "/auth/me"), {
      headers: { Authorization: `Bearer ${access}` },
    });
    return jsonResponse(await upstream.text(), upstream.status);
  } catch {
    return jsonResponse(JSON.stringify({ detail: "service_unavailable" }), 503);
  }
}
