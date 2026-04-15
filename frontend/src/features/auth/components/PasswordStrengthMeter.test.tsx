import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PasswordStrengthMeter } from "./PasswordStrengthMeter";

describe("PasswordStrengthMeter", () => {
  it("renders a score bar with aria-valuenow between 0 and 4", () => {
    render(<PasswordStrengthMeter password="hello" />);
    const bar = screen.getByRole("progressbar");
    const v = Number(bar.getAttribute("aria-valuenow"));
    expect(v).toBeGreaterThanOrEqual(0);
    expect(v).toBeLessThanOrEqual(4);
  });

  it("renders a stronger score for a longer password", () => {
    const { rerender } = render(<PasswordStrengthMeter password="a" />);
    const weak = Number(
      screen.getByRole("progressbar").getAttribute("aria-valuenow"),
    );
    rerender(
      <PasswordStrengthMeter password="correct horse battery staple 2026!" />,
    );
    const strong = Number(
      screen.getByRole("progressbar").getAttribute("aria-valuenow"),
    );
    expect(strong).toBeGreaterThanOrEqual(weak);
  });
});
