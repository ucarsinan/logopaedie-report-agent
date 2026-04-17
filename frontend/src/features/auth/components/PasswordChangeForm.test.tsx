import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PasswordChangeForm } from "./PasswordChangeForm";

describe("PasswordChangeForm", () => {
  afterEach(() => vi.restoreAllMocks());

  it("requires current password field", () => {
    render(<PasswordChangeForm />);
    const current = screen.getByLabelText(/aktuelles passwort/i);
    expect(current).toBeRequired();
  });

  it("disables submit if new password < 12 chars", () => {
    render(<PasswordChangeForm />);
    fireEvent.change(screen.getByLabelText(/aktuelles passwort/i), {
      target: { value: "oldpw1234567890" },
    });
    fireEvent.change(screen.getByLabelText(/neues passwort$/i), {
      target: { value: "short" },
    });
    const btn = screen.getByRole("button", { name: /ändern/i });
    expect(btn).toBeDisabled();
  });

  it("submits and shows success", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    render(<PasswordChangeForm />);
    fireEvent.change(screen.getByLabelText(/aktuelles passwort/i), {
      target: { value: "oldpw1234567890" },
    });
    fireEvent.change(screen.getByLabelText(/neues passwort$/i), {
      target: { value: "newpw1234567890" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ändern/i }));
    await waitFor(() =>
      expect(screen.getByText(/passwort geändert/i)).toBeInTheDocument(),
    );
  });
});
