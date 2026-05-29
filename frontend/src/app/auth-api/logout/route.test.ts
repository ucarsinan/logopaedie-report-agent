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

  it("sends the refresh_token cookie value in the backend body and hits /auth/logout", async () => {
    const spy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));
    const req = new Request("http://localhost:3000/auth-api/logout", {
      method: "POST",
      headers: { cookie: "refresh_token=RT-from-cookie" },
    });
    const res = await POST(req);

    expect(res.status).toBe(200);
    expect(spy).toHaveBeenCalledTimes(1);
    const [url, init] = spy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8001/auth/logout");
    expect(JSON.parse(init.body as string)).toEqual({
      refresh_token: "RT-from-cookie",
    });
  });

  it("short-circuits without a backend call when no refresh_token cookie is present", async () => {
    const spy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));
    const req = new Request("http://localhost:3000/auth-api/logout", {
      method: "POST",
    });
    const res = await POST(req);
    const all = res.headers.getSetCookie().join("\n");

    expect(spy).not.toHaveBeenCalled();
    expect(res.status).toBe(200);
    expect(all).toContain("access_token=");
    expect(all).toContain("refresh_token=");
    expect(all).toContain("Path=/auth-api/refresh");
  });
});
