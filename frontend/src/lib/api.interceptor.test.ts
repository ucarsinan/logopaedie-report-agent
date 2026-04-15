import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { apiCall, __resetRefreshForTest } from "./api";

describe("apiCall single-flight 401 interceptor", () => {
  beforeEach(() => {
    __resetRefreshForTest();
  });
  afterEach(() => vi.restoreAllMocks());

  it("triggers single refresh on 401 and retries once", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock
      .mockResolvedValueOnce(new Response("", { status: 401 }))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(new Response("ok", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const res = await apiCall("/reports");
    expect(res.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toBe("/api/auth/refresh");
  });

  it("parallel 401s share exactly one refresh", async () => {
    const fetchMock = vi.fn<typeof fetch>((url: RequestInfo | URL) => {
      const u = typeof url === "string" ? url : url.toString();
      if (u === "/api/auth/refresh")
        return Promise.resolve(new Response("{}", { status: 200 }));
      return Promise.resolve(new Response("", { status: 401 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const calls = await Promise.allSettled([
      apiCall("/reports"),
      apiCall("/sessions"),
      apiCall("/therapy-plans"),
    ]);
    expect(calls).toHaveLength(3);
    const refreshCalls = fetchMock.mock.calls.filter(
      (c) => c[0] === "/api/auth/refresh",
    );
    expect(refreshCalls).toHaveLength(1);
  });

  it("redirects to /login when refresh fails", async () => {
    const hrefSetter = vi.fn();
    Object.defineProperty(window, "location", {
      value: {
        href: "",
        set href(v: string) {
          hrefSetter(v);
        },
      },
      writable: true,
    });
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock
      .mockResolvedValueOnce(new Response("", { status: 401 }))
      .mockResolvedValueOnce(new Response("", { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);

    await apiCall("/reports");
    expect(hrefSetter).toHaveBeenCalledWith("/login");
  });

  it("bypasses interceptor for /api/auth/* URLs", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(new Response("", { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);

    const res = await apiCall("/api/auth/login");
    expect(res.status).toBe(401);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
