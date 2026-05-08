import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    analysis: {
      phonologicalText: vi.fn(),
    },
  },
}));

vi.mock("@/components/WorkflowStepper", () => ({
  WorkflowStepper: ({ currentStep }: { currentStep: number }) => (
    <div data-testid="workflow-stepper" data-step={currentStep} />
  ),
}));

import { api } from "@/lib/api";
import { PhonologyModule } from "../PhonologyModule";

const mockAnalysisResult = {
  items: [
    {
      target_word: "Sonne",
      production: "Tonne",
      processes: ["Substitution /s/ → /t/"],
      severity: "mittel",
    },
  ],
  summary: "Phonologische Prozesse festgestellt.",
  age_appropriate: false,
  recommended_focus: ["Frikativ-Training"],
};

describe("PhonologyModule", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.analysis.phonologicalText).mockResolvedValue(
      mockAnalysisResult as unknown as ReturnType<typeof api.analysis.phonologicalText> extends Promise<infer T> ? T : never
    );
  });

  it("renders without crash", () => {
    render(<PhonologyModule />);
    expect(screen.getByText(/Phonologische Prozessanalyse/i)).toBeInTheDocument();
  });

  it("has input fields for target word and production", () => {
    render(<PhonologyModule />);
    expect(screen.getByPlaceholderText(/Zielwort/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Produktion/i)).toBeInTheDocument();
  });

  it("has a child age input", () => {
    render(<PhonologyModule />);
    expect(screen.getByPlaceholderText(/z\.B\. 4;6 Jahre/i)).toBeInTheDocument();
  });

  it("has an analyze button", () => {
    render(<PhonologyModule />);
    expect(screen.getByText(/Analyse starten/i)).toBeInTheDocument();
  });

  it("calls analysis API when analyze button clicked with valid word pairs", async () => {
    render(<PhonologyModule />);

    // Fill in word pair
    fireEvent.change(screen.getByPlaceholderText(/Zielwort/i), { target: { value: "Sonne" } });
    fireEvent.change(screen.getByPlaceholderText(/Produktion/i), { target: { value: "Tonne" } });

    fireEvent.click(screen.getByText(/Analyse starten/i));

    await waitFor(() => {
      expect(vi.mocked(api.analysis.phonologicalText)).toHaveBeenCalledWith(
        [{ target: "Sonne", production: "Tonne" }],
        undefined,
      );
    });
  });

  it("does not call API when word pairs are empty", async () => {
    render(<PhonologyModule />);
    // Inputs are empty by default
    fireEvent.click(screen.getByText(/Analyse starten/i));
    await waitFor(() => {
      expect(vi.mocked(api.analysis.phonologicalText)).not.toHaveBeenCalled();
    });
  });

  it("displays analysis results after successful call", async () => {
    render(<PhonologyModule />);

    fireEvent.change(screen.getByPlaceholderText(/Zielwort/i), { target: { value: "Sonne" } });
    fireEvent.change(screen.getByPlaceholderText(/Produktion/i), { target: { value: "Tonne" } });
    fireEvent.click(screen.getByText(/Analyse starten/i));

    await waitFor(() => {
      expect(screen.getByText("Sonne")).toBeInTheDocument();
      expect(screen.getByText("Tonne")).toBeInTheDocument();
      expect(screen.getByText(/Phonologische Prozesse festgestellt/i)).toBeInTheDocument();
    });
  });
});
