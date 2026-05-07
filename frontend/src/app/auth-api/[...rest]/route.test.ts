import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { GET, POST } from "./route";

describe("/auth-api catch-all Route Handler", () => {
  beforeEach(() => {
    process.env.BACKEND_URL = "http://localhost:8001";
  });

  afterEach(() => vi.restoreAllMocks());

  it("forwards allowed authenticated session routes with Bearer token", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ sessions: [] }), { status: 200 }),
    );
    const req = new Request("http://localhost:3000/auth-api/sessions", {
      headers: { cookie: "access_token=AT" },
    });
    await GET(req, { params: Promise.resolve({ rest: ["sessions"] }) });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8001/auth/sessions",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({ Authorization: "Bearer AT" }),
      }),
    );
  });

  it("forwards allowed 2FA setup route", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    const req = new Request("http://localhost:3000/auth-api/2fa/setup", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        cookie: "access_token=AT",
      },
      body: "{}",
    });
    await POST(req, {
      params: Promise.resolve({ rest: ["2fa", "setup"] }),
    });
    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8001/auth/2fa/setup");
  });

  it("keeps unknown auth routes blocked", async () => {
    vi.spyOn(global, "fetch");
    const req = new Request("http://localhost:3000/auth-api/users");
    const res = await GET(req, { params: Promise.resolve({ rest: ["users"] }) });
    expect(res.status).toBe(404);
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
