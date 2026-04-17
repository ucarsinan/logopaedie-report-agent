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

  it("retries with refresh token when me returns 401, then becomes authenticated", async () => {
    const user = {
      id: "u1",
      email: "a@b.c",
      role: "user",
      totp_enabled: false,
      created_at: "2026-04-13T00:00:00Z",
    };
    const fetchMock = vi.fn<typeof fetch>();
    // First me() → 401 (expired access token)
    fetchMock.mockResolvedValueOnce(new Response("{}", { status: 401 }));
    // refresh → 200
    fetchMock.mockResolvedValueOnce(new Response("{}", { status: 200 }));
    // Second me() → 200 with user
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(user), { status: 200 }),
    );
    vi.spyOn(global, "fetch").mockImplementation(fetchMock);

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("status").textContent).toBe("authenticated"),
    );
  });

  it("marks unauthenticated when both me and refresh return 401", async () => {
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
