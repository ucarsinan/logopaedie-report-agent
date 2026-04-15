import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TwoFactorDisable } from "./TwoFactorDisable";

describe("TwoFactorDisable", () => {
  afterEach(() => vi.restoreAllMocks());

  it("requires both password and 6-digit code", () => {
    render(<TwoFactorDisable />);
    const btn = screen.getByRole("button", { name: /deaktivieren/i });
    expect(btn).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/aktuelles passwort/i), {
      target: { value: "pw1234567890" },
    });
    expect(btn).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/6-stelliger code/i), {
      target: { value: "123456" },
    });
    expect(btn).not.toBeDisabled();
  });
});
