import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { POST } from "./route";

describe("POST /api/auth/refresh Route Handler", () => {
  beforeEach(() => {
    process.env.BACKEND_URL = "http://localhost:8001";
  });
  afterEach(() => vi.restoreAllMocks());

  it("rotates access_token and refresh_token cookies on success", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ access_token: "NEW_AT", refresh_token: "NEW_RT" }),
        { status: 200 },
      ),
    );
    const req = new Request("http://localhost:3000/api/auth/refresh", {
      method: "POST",
      headers: { cookie: "refresh_token=OLD_RT" },
    });
    const res = await POST(req);
    expect(res.status).toBe(200);
    const all = res.headers.getSetCookie().join("\n");
    expect(all).toContain("access_token=NEW_AT");
    expect(all).toContain("refresh_token=NEW_RT");
  });

  it("returns 401 with no cookies when refresh token is missing", async () => {
    const req = new Request("http://localhost:3000/api/auth/refresh", {
      method: "POST",
    });
    const res = await POST(req);
    expect(res.status).toBe(401);
    expect(res.headers.getSetCookie()).toHaveLength(0);
  });
});
