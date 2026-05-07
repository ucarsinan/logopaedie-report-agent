import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AuthProvider } from "@/providers/AuthProvider";
import { UserAccountBar } from "./UserAccountBar";

const user = {
  id: "u1",
  email: "therapeutin@example.com",
  role: "user",
  totp_enabled: true,
  created_at: "2026-04-13T00:00:00Z",
};

function renderWithAuth() {
  return render(
    <AuthProvider>
      <UserAccountBar />
    </AuthProvider>,
  );
}

describe("UserAccountBar", () => {
  beforeEach(() => {
    Object.defineProperty(window, "location", {
      value: { href: "" },
      writable: true,
    });
  });

  afterEach(() => vi.restoreAllMocks());

  it("shows the authenticated user's account details", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(user), { status: 200 }),
    );

    renderWithAuth();

    expect(await screen.findByText("therapeutin@example.com")).toBeInTheDocument();
    expect(screen.getByText("Benutzer")).toBeInTheDocument();
    expect(screen.getByText("2FA aktiv")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /abmelden/i })).toBeInTheDocument();
  });

  it("logs out and redirects to login", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(user), { status: 200 }),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    vi.spyOn(global, "fetch").mockImplementation(fetchMock);

    renderWithAuth();

    fireEvent.click(await screen.findByRole("button", { name: /abmelden/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/auth-api/logout",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    await waitFor(() => expect(window.location.href).toBe("/login"));
  });
});
