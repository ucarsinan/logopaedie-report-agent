import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import VerifyEmailPage from "./page";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("?token=abc123"),
}));

describe("VerifyEmailPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("calls /api/auth/verify-email with token and shows success", async () => {
    const spy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    render(<VerifyEmailPage />);
    await waitFor(() =>
      expect(screen.getByText(/email.*bestätigt/i)).toBeInTheDocument(),
    );
    const call = spy.mock.calls[0];
    expect(call[0]).toBe("/api/auth/verify-email");
    expect(JSON.parse((call[1] as RequestInit).body as string)).toEqual({
      token: "abc123",
    });
  });

  it("shows error message on 400", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "invalid" }), { status: 400 }),
    );
    render(<VerifyEmailPage />);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toBeInTheDocument(),
    );
  });
});
