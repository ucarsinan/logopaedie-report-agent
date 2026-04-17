import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { POST } from "./route";

describe("POST /api/auth/login Route Handler", () => {
  beforeEach(() => {
    process.env.BACKEND_URL = "http://localhost:8001";
  });
  afterEach(() => vi.restoreAllMocks());

  it("sets access_token, refresh_token, user_role cookies on success", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "AT",
          refresh_token: "RT",
          user: {
            id: "u1",
            email: "a@b.c",
            role: "admin",
            totp_enabled: false,
            created_at: "",
          },
        }),
        { status: 200 },
      ),
    );

    const req = new Request("http://localhost:3000/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: "a@b.c", password: "pw1234567890" }),
    });
    const res = await POST(req);
    expect(res.status).toBe(200);

    const cookies = res.headers.getSetCookie();
    const all = cookies.join("\n");
    expect(all).toContain("access_token=AT");
    expect(all).toContain("refresh_token=RT");
    expect(all).toContain("user_role=admin");
    expect(all).toContain("HttpOnly");
    expect(all).toContain("SameSite=lax");
    expect(all).toContain("Path=/");
  });

  it("forwards 2fa_required response without setting cookies", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ step: "2fa_required", challenge_id: "c1" }),
        { status: 200 },
      ),
    );
    const req = new Request("http://localhost:3000/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: "a@b.c", password: "pw1234567890" }),
    });
    const res = await POST(req);
    const body = await res.json();
    expect(body).toEqual({ step: "2fa_required", challenge_id: "c1" });
    expect(res.headers.getSetCookie()).toEqual([]);
  });

  it("forwards backend error status", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid" }), { status: 401 }),
    );
    const req = new Request("http://localhost:3000/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: "a@b.c", password: "wrong" }),
    });
    const res = await POST(req);
    expect(res.status).toBe(401);
  });
});
