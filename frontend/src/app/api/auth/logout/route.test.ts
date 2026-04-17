import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { POST } from "./route";

describe("POST /api/auth/logout Route Handler", () => {
  beforeEach(() => {
    process.env.BACKEND_URL = "http://localhost:8001";
  });
  afterEach(() => vi.restoreAllMocks());

  it("clears access_token, refresh_token, user_role cookies", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    const req = new Request("http://localhost:3000/api/auth/logout", {
      method: "POST",
      headers: { cookie: "refresh_token=RT; access_token=AT" },
    });
    const res = await POST(req);
    expect(res.status).toBe(200);
    const all = res.headers.getSetCookie().join("\n");
    expect(all).toMatch(/access_token=;/);
    expect(all).toMatch(/refresh_token=;/);
    expect(all).toMatch(/user_role=;/);
    expect(all).toContain("Max-Age=0");
  });
});
