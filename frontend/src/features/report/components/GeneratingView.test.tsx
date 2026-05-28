import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GeneratingView } from "./GeneratingView";

describe("GeneratingView", () => {
  it("renders a layout-aware skeleton with an accessible live region", () => {
    render(<GeneratingView />);

    const region = screen.getByRole("status");
    expect(region).toHaveAttribute("aria-live", "polite");
    expect(region).toHaveAttribute("aria-label", "Bericht wird generiert");
    expect(screen.getByTestId("report-generating-skeleton")).toBeInTheDocument();
  });

  it("renders the announcement copy alongside the skeleton", () => {
    render(<GeneratingView />);

    expect(screen.getByText(/KI analysiert die Anamnese/i)).toBeInTheDocument();
    expect(screen.getByText(/10–20 Sekunden/i)).toBeInTheDocument();
  });
});
