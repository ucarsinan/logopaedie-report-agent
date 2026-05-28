import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

  it("shows a layout-aware skeleton while generation is pending and renders the plan once it resolves", async () => {
    const mockReports = {
      items: [
        {
          id: 7,
          pseudonym: "Patient-A",
          report_type: "befundbericht",
          created_at: "2026-05-01T10:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      limit: 20,
    };
    vi.mocked(api.reports.list).mockResolvedValue(
      mockReports as unknown as ReturnType<typeof api.reports.list> extends Promise<infer T> ? T : never,
    );
    vi.mocked(api.sessions.create).mockResolvedValue({
      session_id: "abc123def456",
      collected_data: {},
    } as unknown as ReturnType<typeof api.sessions.create> extends Promise<infer T> ? T : never);

    const mockPlan = {
      patient_pseudonym: "Patient-A",
      diagnose_text: "Sprachentwicklungsstörung",
      frequency: "2x pro Woche",
      total_sessions: 20,
      plan_phases: [
        {
          phase_name: "Phase 1",
          duration: "4 Wochen",
          goals: [
            {
              icf_code: "b167",
              goal_text: "Wortschatz erweitern",
              methods: ["Bildkarten"],
              milestones: ["Stufe 1"],
              timeframe: "2 Wochen",
            },
          ],
        },
      ],
      elternberatung: "",
      haeusliche_uebungen: [],
    };

    let resolvePlan: (v: typeof mockPlan) => void = () => {};
    const pending = new Promise<typeof mockPlan>((res) => {
      resolvePlan = res;
    });
    vi.mocked(api.sessions.therapyPlan).mockReturnValue(
      pending as unknown as ReturnType<typeof api.sessions.therapyPlan>,
    );

    render(<TherapyPlanModule sessionId={null} />);

    fireEvent.click(await screen.findByText(/Aus Bericht/i));

    const select = await screen.findByRole("combobox");
    fireEvent.change(select, { target: { value: "7" } });
    fireEvent.click(screen.getByText(/^Generieren$/));

    const skeleton = await screen.findByTestId("therapy-plan-generating-skeleton");
    expect(skeleton).toBeInTheDocument();
    expect(screen.queryByText(/Therapieplan: Patient-A/)).not.toBeInTheDocument();

    resolvePlan(mockPlan);

    await waitFor(() => {
      expect(screen.queryByTestId("therapy-plan-generating-skeleton")).not.toBeInTheDocument();
    });
    expect(screen.getByText(/Therapieplan: Patient-A/)).toBeInTheDocument();
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
