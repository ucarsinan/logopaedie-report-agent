import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { OnboardingOverlay } from "../OnboardingOverlay";

describe("OnboardingOverlay", () => {
  const onComplete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders as a labelled modal dialog", () => {
    render(<OnboardingOverlay onComplete={onComplete} />);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute("aria-modal", "true");

    const labelId = dialog.getAttribute("aria-labelledby");
    expect(labelId).toBeTruthy();
    const heading = document.getElementById(labelId as string);
    expect(heading).not.toBeNull();
    expect(heading?.tagName).toBe("H2");
    expect(heading?.textContent).toBeTruthy();
  });

  it("calls onComplete when Escape is pressed", () => {
    render(<OnboardingOverlay onComplete={onComplete} />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it("moves focus to the first interactive element on mount", () => {
    render(<OnboardingOverlay onComplete={onComplete} />);

    const dialog = screen.getByRole("dialog");
    const active = document.activeElement;
    expect(active).not.toBe(document.body);
    expect(dialog.contains(active)).toBe(true);
    expect((active as HTMLElement).tagName).toBe("BUTTON");
  });

  it("returns focus to the previously focused element on unmount", () => {
    const trigger = document.createElement("button");
    trigger.textContent = "Open";
    document.body.appendChild(trigger);
    trigger.focus();
    expect(document.activeElement).toBe(trigger);

    const { unmount } = render(<OnboardingOverlay onComplete={onComplete} />);
    expect(document.activeElement).not.toBe(trigger);

    act(() => {
      unmount();
    });

    expect(document.activeElement).toBe(trigger);
    document.body.removeChild(trigger);
  });
});
