import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ResetPasswordPage from "./page";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("?token=r1"),
}));

describe("ResetPasswordPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("requires password confirmation to match", () => {
    render(<ResetPasswordPage />);
    fireEvent.change(screen.getByLabelText(/neues passwort$/i), {
      target: { value: "pw1234567890" },
    });
    fireEvent.change(screen.getByLabelText(/passwort bestätigen/i), {
      target: { value: "different12345" },
    });
    const btn = screen.getByRole("button", { name: /zurücksetzen/i });
    expect(btn).toBeDisabled();
  });
});
