import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ActiveSessionsList } from "./ActiveSessionsList";

const sessions = [
  {
    id: "s1",
    user_agent: "Chrome",
    ip_address: "1.2.3.4",
    created_at: "2026-04-13T10:00:00Z",
    last_used_at: "2026-04-13T11:00:00Z",
    expires_at: "2026-04-20T00:00:00Z",
    is_current: true,
  },
  {
    id: "s2",
    user_agent: "Firefox",
    ip_address: "5.6.7.8",
    created_at: "2026-04-12T10:00:00Z",
    last_used_at: "2026-04-12T11:00:00Z",
    expires_at: "2026-04-19T00:00:00Z",
    is_current: false,
  },
];

describe("ActiveSessionsList", () => {
  beforeEach(() => {
    Object.defineProperty(window, "location", {
      value: { href: "" },
      writable: true,
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it("marks current session with a badge", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(sessions), { status: 200 }),
    );
    render(<ActiveSessionsList />);
    await screen.findByText("Chrome");
    expect(screen.getByText(/dieses gerät/i)).toBeInTheDocument();
  });

  it("revoking a non-current session removes the row", async () => {
    const spy = vi.spyOn(global, "fetch");
    spy.mockResolvedValueOnce(
      new Response(JSON.stringify(sessions), { status: 200 }),
    );
    spy.mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    render(<ActiveSessionsList />);
    await screen.findByText("Firefox");
    const revokeBtns = screen.getAllByRole("button", { name: /widerrufen/i });
    fireEvent.click(revokeBtns[1]);
    await waitFor(() =>
      expect(screen.queryByText("Firefox")).not.toBeInTheDocument(),
    );
  });

  it("revoking current session redirects to /login", async () => {
    const spy = vi.spyOn(global, "fetch");
    spy.mockResolvedValueOnce(
      new Response(JSON.stringify(sessions), { status: 200 }),
    );
    spy.mockResolvedValueOnce(
      new Response(JSON.stringify({ current_session_revoked: true }), {
        status: 200,
      }),
    );
    render(<ActiveSessionsList />);
    await screen.findByText("Chrome");
    const revokeBtns = screen.getAllByRole("button", { name: /widerrufen/i });
    fireEvent.click(revokeBtns[0]);
    await waitFor(() => expect(window.location.href).toBe("/login"));
  });
});
