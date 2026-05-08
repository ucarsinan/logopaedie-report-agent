import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    analysis: {
      compare: vi.fn(),
    },
  },
}));

vi.mock("@/components/WorkflowStepper", () => ({
  WorkflowStepper: ({ currentStep }: { currentStep: number }) => (
    <div data-testid="workflow-stepper" data-step={currentStep} />
  ),
}));

import { api } from "@/lib/api";
import { CompareModule } from "../CompareModule";

const mockCompareResult = {
  items: [
    {
      category: "Artikulation",
      initial_finding: "Schwere Beeinträchtigung",
      current_finding: "Leichte Beeinträchtigung",
      change: "verbessert",
    },
  ],
  overall_progress: "Deutlicher Fortschritt erzielt.",
  remaining_issues: ["Stimmeinsatz"],
  recommendation: "Therapie fortsetzen.",
};

describe("CompareModule", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.analysis.compare).mockResolvedValue(
      mockCompareResult as unknown as ReturnType<typeof api.analysis.compare> extends Promise<infer T> ? T : never
    );
  });

  it("renders without crash", () => {
    render(<CompareModule />);
    expect(screen.getByText(/Vergleichende Berichtsanalyse/i)).toBeInTheDocument();
  });

  it("shows workflow stepper", () => {
    render(<CompareModule />);
    expect(screen.getByTestId("workflow-stepper")).toBeInTheDocument();
  });

  it("has file upload area for initial report", () => {
    render(<CompareModule />);
    expect(screen.getAllByText(/Erstbefund/i).length).toBeGreaterThan(0);
  });

  it("has file upload area for current report", () => {
    render(<CompareModule />);
    expect(screen.getByText(/Aktueller Bericht/i)).toBeInTheDocument();
  });

  it("has two file inputs", () => {
    render(<CompareModule />);
    // file inputs don't have textbox role, check for input[type=file]
    const inputs = document.querySelectorAll("input[type='file']");
    expect(inputs.length).toBe(2);
  });

  it("has a compare button", () => {
    render(<CompareModule />);
    expect(screen.getByText(/Berichte vergleichen/i)).toBeInTheDocument();
  });

  it("shows error when no files selected", async () => {
    render(<CompareModule />);
    fireEvent.click(screen.getByText(/Berichte vergleichen/i));
    await waitFor(() => {
      expect(screen.getByText(/Bitte wählen Sie beide Berichte aus/i)).toBeInTheDocument();
    });
  });
});
