import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    patients: {
      progress: vi.fn(),
    },
  },
}));

import { api } from "@/lib/api";
import { ProgressSnapshot } from "../ProgressSnapshot";

const mockProgressResponse = {
  message: null,
  comparison: {
    items: [
      {
        category: "Artikulation",
        initial_finding: "Schwere Beeinträchtigung",
        current_finding: "Leichte Beeinträchtigung",
        change: "verbessert",
        details: "Deutliche Verbesserung",
      },
    ],
    overall_progress: "Deutlicher Fortschritt erzielt.",
    remaining_issues: ["Stimmeinsatz"],
    recommendation: "Therapie fortsetzen.",
  },
};

describe("ProgressSnapshot", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls api.patients.progress with patientId", async () => {
    vi.mocked(api.patients.progress).mockResolvedValue(
      mockProgressResponse as unknown as ReturnType<typeof api.patients.progress> extends Promise<infer T> ? T : never
    );

    render(<ProgressSnapshot patientId="patient-123" />);

    await waitFor(() => {
      expect(vi.mocked(api.patients.progress)).toHaveBeenCalledWith("patient-123");
    });
  });

  it("shows loading state initially", () => {
    vi.mocked(api.patients.progress).mockReturnValue(new Promise(() => {}));
    render(<ProgressSnapshot patientId="patient-123" />);
    expect(screen.getByText(/Lade Fortschritt/i)).toBeInTheDocument();
  });

  it("displays overall progress after loading", async () => {
    vi.mocked(api.patients.progress).mockResolvedValue(
      mockProgressResponse as unknown as ReturnType<typeof api.patients.progress> extends Promise<infer T> ? T : never
    );

    render(<ProgressSnapshot patientId="patient-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Deutlicher Fortschritt erzielt/i)).toBeInTheDocument();
    });
  });

  it("displays comparison items after loading", async () => {
    vi.mocked(api.patients.progress).mockResolvedValue(
      mockProgressResponse as unknown as ReturnType<typeof api.patients.progress> extends Promise<infer T> ? T : never
    );

    render(<ProgressSnapshot patientId="patient-123" />);

    await waitFor(() => {
      expect(screen.getByText("Artikulation")).toBeInTheDocument();
    });
  });

  it("handles API error gracefully", async () => {
    vi.mocked(api.patients.progress).mockRejectedValue(new Error("Verbindungsfehler"));

    render(<ProgressSnapshot patientId="patient-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Verbindungsfehler/i)).toBeInTheDocument();
    });
  });

  it("shows empty message when no comparison data", async () => {
    vi.mocked(api.patients.progress).mockResolvedValue({
      message: "Noch kein Fortschrittsvergleich vorhanden.",
      comparison: null,
    } as unknown as ReturnType<typeof api.patients.progress> extends Promise<infer T> ? T : never);

    render(<ProgressSnapshot patientId="patient-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Noch kein Fortschrittsvergleich vorhanden/i)).toBeInTheDocument();
    });
  });

  it("shows recommendation when available", async () => {
    vi.mocked(api.patients.progress).mockResolvedValue(
      mockProgressResponse as unknown as ReturnType<typeof api.patients.progress> extends Promise<infer T> ? T : never
    );

    render(<ProgressSnapshot patientId="patient-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Therapie fortsetzen/i)).toBeInTheDocument();
    });
  });
});
