import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WorkflowStepper, type StepConfig } from "../WorkflowStepper";

const steps: StepConfig[] = [
  { label: "Aufnahme", infoTitle: "", infoText: "" },
  { label: "Analyse", infoTitle: "", infoText: "" },
  { label: "Bericht", infoTitle: "", infoText: "" },
];

describe("WorkflowStepper", () => {
  it("wraps the steps in a nav with German aria-label", () => {
    render(<WorkflowStepper steps={steps} currentStep={1} />);
    const nav = screen.getByRole("navigation", { name: "Arbeitsschritte" });
    expect(nav).toBeInTheDocument();
  });

  it("marks the active step with aria-current=step and labels position + status", () => {
    render(<WorkflowStepper steps={steps} currentStep={1} />);

    const active = screen.getByRole("button", {
      name: "Schritt 2: Analyse, aktiv",
    });
    expect(active).toHaveAttribute("aria-current", "step");

    const done = screen.getByRole("button", {
      name: "Schritt 1: Aufnahme, abgeschlossen",
    });
    expect(done).not.toHaveAttribute("aria-current");

    const pending = screen.getByRole("button", {
      name: "Schritt 3: Bericht, noch nicht verfügbar",
    });
    expect(pending).not.toHaveAttribute("aria-current");
    expect(pending).toBeDisabled();
  });
});
