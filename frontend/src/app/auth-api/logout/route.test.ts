import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { POST } from "./route";

describe("POST /auth-api/logout Route Handler", () => {
  beforeEach(() => {
    process.env.BACKEND_URL = "http://localhost:8001";
  });

  afterEach(() => vi.restoreAllMocks());

  it("clears auth cookies", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(new Response("{}", { status: 200 }));
    const req = new Request("http://localhost:3000/auth-api/logout", {
      method: "POST",
      headers: { cookie: "refresh_token=RT" },
    });
    const res = await POST(req);
    const all = res.headers.getSetCookie().join("\n");
    expect(res.status).toBe(200);
    expect(all).toContain("access_token=");
    expect(all).toContain("refresh_token=");
    expect(all).toContain("Path=/auth-api/refresh");
  });
});
