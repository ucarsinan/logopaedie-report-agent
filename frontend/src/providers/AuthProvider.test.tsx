import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { AuthProvider, useAuthContext } from "./AuthProvider";

function Probe() {
  const { state } = useAuthContext();
  return <div data-testid="status">{state.status}</div>;
}

describe("AuthProvider", () => {
  afterEach(() => vi.restoreAllMocks());

  it("loads /api/auth/me on mount and becomes authenticated", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "u1",
          email: "a@b.c",
          role: "user",
          totp_enabled: false,
          created_at: "2026-04-13T00:00:00Z",
        }),
        { status: 200 },
      ),
    );
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("status").textContent).toBe("authenticated"),
    );
  });

  it("marks unauthenticated when /api/auth/me returns 401", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("{}", { status: 401 }),
    );
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("status").textContent).toBe("unauthenticated"),
    );
  });
});
