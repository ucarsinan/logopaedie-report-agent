import { backendTarget, jsonResponse } from "../../_lib/backend-proxy";

export async function POST(req: Request): Promise<Response> {
  const body = await req.text();
  const upstream = await fetch(backendTarget(req, "/auth/register"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  return jsonResponse(await upstream.text(), upstream.status);
}
