import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { GET, POST } from "./route";

describe("/api/auth catch-all Route Handler", () => {
  beforeEach(() => {
    process.env.BACKEND_URL = "http://localhost:8001";
  });

  afterEach(() => vi.restoreAllMocks());

  it("forwards allowed authenticated session routes with Bearer token", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const req = new Request("http://localhost:3000/api/auth/sessions", {
      headers: { cookie: "access_token=AT" },
    });

    const res = await GET(req, {
      params: Promise.resolve({ rest: ["sessions"] }),
    });

    expect(res.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8001/auth/sessions",
      expect.objectContaining({
        method: "GET",
        headers: expect.any(Object),
      }),
    );
    expect(
      (fetchMock.mock.calls[0][1]?.headers as Record<string, string>)
        .Authorization,
    ).toBe("Bearer AT");
  });

  it("forwards allowed 2fa routes", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const req = new Request("http://localhost:3000/api/auth/2fa/setup", {
      method: "POST",
      headers: { cookie: "access_token=AT" },
    });

    const res = await POST(req, {
      params: Promise.resolve({ rest: ["2fa", "setup"] }),
    });

    expect(res.status).toBe(200);
    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://localhost:8001/auth/2fa/setup",
    );
  });

  it("keeps unknown auth routes blocked", async () => {
    const fetchMock = vi.spyOn(global, "fetch");
    const req = new Request("http://localhost:3000/api/auth/users");

    const res = await GET(req, {
      params: Promise.resolve({ rest: ["users"] }),
    });

    expect(res.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
