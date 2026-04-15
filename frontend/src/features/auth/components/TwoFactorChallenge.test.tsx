import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TwoFactorChallenge } from "./TwoFactorChallenge";

describe("TwoFactorChallenge", () => {
  it("calls onSubmit with a 6-digit code", () => {
    const onSubmit = vi.fn();
    render(<TwoFactorChallenge onSubmit={onSubmit} loading={false} />);
    const input = screen.getByLabelText(/6-stelliger Code/i);
    fireEvent.change(input, { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: /bestätigen/i }));
    expect(onSubmit).toHaveBeenCalledWith("123456");
  });

  it("disables submit when code length != 6", () => {
    render(<TwoFactorChallenge onSubmit={() => {}} loading={false} />);
    const btn = screen.getByRole("button", { name: /bestätigen/i });
    fireEvent.change(screen.getByLabelText(/6-stelliger Code/i), {
      target: { value: "12345" },
    });
    expect(btn).toBeDisabled();
  });
});
