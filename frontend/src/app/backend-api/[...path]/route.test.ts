import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { GET, POST } from "./route";

describe("/backend-api backend proxy Route Handler", () => {
  beforeEach(() => {
    process.env.BACKEND_URL = "http://localhost:8001";
  });

  afterEach(() => vi.restoreAllMocks());

  it("forwards access_token cookie as a Bearer token", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const req = new Request("http://localhost:3000/backend-api/sessions?mode=report", {
      headers: { cookie: "access_token=AT" },
    });

    const res = await GET(req, {
      params: Promise.resolve({ path: ["sessions"] }),
    });

    expect(res.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8001/sessions?mode=report",
      expect.objectContaining({
        method: "GET",
        headers: expect.any(Headers),
      }),
    );
    const headers = fetchMock.mock.calls[0][1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer AT");
  });

  it("preserves JSON request bodies", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ session_id: "abc" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const req = new Request("http://localhost:3000/backend-api/sessions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        cookie: "access_token=AT",
      },
      body: JSON.stringify({ mode: "report" }),
    });

    await POST(req, {
      params: Promise.resolve({ path: ["sessions"] }),
    });

    const init = fetchMock.mock.calls[0][1];
    expect(init?.body).toBeInstanceOf(ArrayBuffer);
    expect(new TextDecoder().decode(init?.body as ArrayBuffer)).toBe(
      JSON.stringify({ mode: "report" }),
    );
  });
});
