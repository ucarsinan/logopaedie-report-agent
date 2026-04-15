import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { POST } from "./route";

describe("POST /api/auth/login/2fa Route Handler", () => {
  beforeEach(() => {
    process.env.BACKEND_URL = "http://localhost:8001";
  });
  afterEach(() => vi.restoreAllMocks());

  it("sets cookies on successful 2FA verification", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "AT2",
          refresh_token: "RT2",
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
    const req = new Request("http://localhost:3000/api/auth/login/2fa", {
      method: "POST",
      body: JSON.stringify({ challenge_id: "c1", code: "123456" }),
    });
    const res = await POST(req);
    expect(res.status).toBe(200);
    const all = res.headers.getSetCookie().join("\n");
    expect(all).toContain("access_token=AT2");
    expect(all).toContain("refresh_token=RT2");
    expect(all).toContain("user_role=user");
  });
});
