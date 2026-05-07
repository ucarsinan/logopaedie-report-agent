import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { POST } from "./route";

describe("POST /auth-api/refresh Route Handler", () => {
  beforeEach(() => {
    process.env.BACKEND_URL = "http://localhost:8001";
  });

  afterEach(() => vi.restoreAllMocks());

  it("returns 401 when refresh cookie is missing", async () => {
    const req = new Request("http://localhost:3000/auth-api/refresh", {
      method: "POST",
    });
    const res = await POST(req);
    expect(res.status).toBe(401);
  });

  it("rotates cookies when backend refresh succeeds", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ access_token: "AT2", refresh_token: "RT2" }), {
        status: 200,
      }),
    );
    const req = new Request("http://localhost:3000/auth-api/refresh", {
      method: "POST",
      headers: { cookie: "refresh_token=RT1" },
    });
    const res = await POST(req);
    const all = res.headers.getSetCookie().join("\n");
    expect(res.status).toBe(200);
    expect(all).toContain("access_token=AT2");
    expect(all).toContain("refresh_token=RT2");
    expect(all).toContain("Path=/auth-api/refresh");
  });
});
