import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    therapyPlans: {
      list: vi.fn(),
      save: vi.fn(),
      update: vi.fn(),
      get: vi.fn(),
    },
    reports: {
      list: vi.fn(),
    },
    sessions: {
      create: vi.fn(),
      chat: vi.fn(),
      therapyPlan: vi.fn(),
    },
  },
}));

vi.mock("@/components/WorkflowStepper", () => ({
  WorkflowStepper: ({ currentStep }: { currentStep: number }) => (
    <div data-testid="workflow-stepper" data-step={currentStep} />
  ),
}));

import { api } from "@/lib/api";
import { TherapyPlanModule } from "../TherapyPlanModule";

describe("TherapyPlanModule", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.therapyPlans.list).mockResolvedValue([]);
    vi.mocked(api.reports.list).mockResolvedValue({ items: [], total: 0, page: 1, limit: 20 });
  });

  it("renders without crash", () => {
    render(<TherapyPlanModule sessionId={null} />);
    expect(screen.getByText(/KI-gestützter Therapieplan/i)).toBeInTheDocument();
  });

  it("shows workflow stepper", () => {
    render(<TherapyPlanModule sessionId={null} />);
    expect(screen.getByTestId("workflow-stepper")).toBeInTheDocument();
  });

  it("shows mode selection buttons", async () => {
    render(<TherapyPlanModule sessionId={null} />);
    await waitFor(() => {
      expect(screen.getByText(/Neu \(Mini-Chat\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Aus Bericht/i)).toBeInTheDocument();
    });
  });

  it("fetches therapy plans and reports on mount", async () => {
    render(<TherapyPlanModule sessionId={null} />);
    await waitFor(() => {
      expect(vi.mocked(api.therapyPlans.list)).toHaveBeenCalledTimes(1);
      expect(vi.mocked(api.reports.list)).toHaveBeenCalledTimes(1);
    });
  });

  it("displays saved plans when available", async () => {
    vi.mocked(api.therapyPlans.list).mockResolvedValue([
      {
        id: 1,
        patient_pseudonym: "Test-Patient",
        created_at: "2024-01-01T10:00:00Z",
        report_id: null,
        session_id: "abc123",
      },
    ] as unknown as ReturnType<typeof api.therapyPlans.list> extends Promise<infer T> ? T : never);

    render(<TherapyPlanModule sessionId={null} />);
    await waitFor(() => {
      expect(screen.getByText("Test-Patient")).toBeInTheDocument();
    });
  });
});
