import { describe, it, expect } from "vitest";
import type { User, AuthState } from "./types";

describe("auth types", () => {
  it("User has id, email, role, totp_enabled, created_at", () => {
    const u: User = {
      id: "u1",
      email: "x@y.z",
      role: "user",
      totp_enabled: false,
      created_at: "2026-04-13T00:00:00Z",
    };
    expect(u.role).toBe("user");
  });

  it("AuthState supports loading | authenticated | unauthenticated", () => {
    const a: AuthState = { status: "loading" };
    const b: AuthState = {
      status: "authenticated",
      user: {
        id: "u1",
        email: "x@y.z",
        role: "admin",
        totp_enabled: true,
        created_at: "",
      },
    };
    const c: AuthState = { status: "unauthenticated" };
    expect([a.status, b.status, c.status]).toEqual([
      "loading",
      "authenticated",
      "unauthenticated",
    ]);
  });
});
