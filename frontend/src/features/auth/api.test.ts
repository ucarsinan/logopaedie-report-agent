import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { authApi } from "./api";

describe("authApi", () => {
  beforeEach(() => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("login POSTs to /auth-api/login with credentials include", async () => {
    await authApi.login("a@b.c", "pw123456789012");
    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock
      .calls[0];
    expect(call[0]).toBe("/auth-api/login");
    expect(call[1].method).toBe("POST");
    expect(call[1].credentials).toBe("include");
    expect(JSON.parse(call[1].body)).toEqual({
      email: "a@b.c",
      password: "pw123456789012",
    });
  });

  it("me GETs /auth-api/me", async () => {
    await authApi.me();
    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock
      .calls[0];
    expect(call[0]).toBe("/auth-api/me");
  });

  it("logout POSTs /auth-api/logout", async () => {
    await authApi.logout();
    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock
      .calls[0];
    expect(call[0]).toBe("/auth-api/logout");
    expect(call[1].method).toBe("POST");
  });
});
