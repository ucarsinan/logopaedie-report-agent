import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { POST } from "./route";

describe("POST /auth-api/login/2fa Route Handler", () => {
  beforeEach(() => {
    process.env.BACKEND_URL = "http://localhost:8001";
  });

  afterEach(() => vi.restoreAllMocks());

  it("sets cookies after successful 2FA login", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "AT",
          refresh_token: "RT",
          user: {
            id: "u1",
            email: "a@b.c",
            role: "user",
            totp_enabled: true,
            created_at: "",
          },
        }),
        { status: 200 },
      ),
    );

    const req = new Request("http://localhost:3000/auth-api/login/2fa", {
      method: "POST",
      body: JSON.stringify({ challenge_id: "c1", code: "123456" }),
    });
    const res = await POST(req);
    const all = res.headers.getSetCookie().join("\n");
    expect(res.status).toBe(200);
    expect(all).toContain("access_token=AT");
    expect(all).toContain("refresh_token=RT");
    expect(all).toContain("Path=/auth-api/refresh");
  });
});
