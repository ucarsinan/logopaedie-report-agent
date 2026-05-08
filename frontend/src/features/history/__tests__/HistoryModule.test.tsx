import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode; [key: string]: unknown }) => (
    <a href={href} {...rest}>{children}</a>
  ),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("react-markdown", () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("remark-gfm", () => ({ default: () => {} }));

vi.mock("@/lib/api", () => ({
  api: {
    reports: {
      list: vi.fn(),
      get: vi.fn(),
      stats: vi.fn(),
      downloadPdf: vi.fn(),
    },
    soap: {
      getByReport: vi.fn(),
    },
  },
}));

vi.mock("../components/FilterBar", () => ({
  FilterBar: ({ onFilterChange }: { onFilterChange: (f: unknown) => void }) => (
    <div data-testid="filter-bar">
      <button onClick={() => onFilterChange({})}>Filter</button>
    </div>
  ),
}));

vi.mock("../components/StatsCards", () => ({
  StatsCards: () => <div data-testid="stats-cards" />,
}));

import { api } from "@/lib/api";
import { HistoryModule } from "../HistoryModule";

const mockReport = {
  id: 1,
  pseudonym: "Test-Patient",
  report_type: "befundbericht",
  created_at: "2024-01-01T10:00:00Z",
  patient_id: null,
  patient_pseudonym: null,
};

describe("HistoryModule", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.reports.list).mockResolvedValue({ items: [], total: 0, page: 1, limit: 20 });
    vi.mocked(api.reports.stats).mockResolvedValue({
      total: 0,
      by_type: {},
      recent_count: 0,
    } as unknown as ReturnType<typeof api.reports.stats> extends Promise<infer T> ? T : never);
    vi.mocked(api.reports.get).mockResolvedValue(null as unknown as ReturnType<typeof api.reports.get> extends Promise<infer T> ? T : never);
    vi.mocked(api.soap.getByReport).mockRejectedValue(new Error("Not found"));
  });

  it("renders without crash", async () => {
    render(<HistoryModule />);
    expect(screen.getByText(/Gespeicherte Berichte/i)).toBeInTheDocument();
  });

  it("fetches reports on mount", async () => {
    render(<HistoryModule />);
    await waitFor(() => {
      expect(vi.mocked(api.reports.list)).toHaveBeenCalledTimes(1);
    });
  });

  it("shows empty state when no reports", async () => {
    render(<HistoryModule />);
    await waitFor(() => {
      expect(screen.getByText(/Noch keine Berichte gespeichert/i)).toBeInTheDocument();
    });
  });

  it("displays reports after loading", async () => {
    vi.mocked(api.reports.list).mockResolvedValue({
      items: [mockReport],
      total: 1,
      page: 1,
      limit: 20,
    });
    render(<HistoryModule />);
    await waitFor(() => {
      expect(screen.getByText("Test-Patient")).toBeInTheDocument();
    });
  });

  it("calls api.reports.get when report is clicked", async () => {
    vi.mocked(api.reports.list).mockResolvedValue({
      items: [mockReport],
      total: 1,
      page: 1,
      limit: 20,
    });
    vi.mocked(api.reports.get).mockResolvedValue({
      id: 1,
      report_type: "befundbericht",
      created_at: "2024-01-01T10:00:00Z",
      patient: { pseudonym: "Test-Patient", age_group: "Erwachsene" },
    } as unknown as ReturnType<typeof api.reports.get> extends Promise<infer T> ? T : never);

    render(<HistoryModule />);
    await waitFor(() => {
      expect(screen.getByText("Test-Patient")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Test-Patient").closest("button")!);

    await waitFor(() => {
      expect(vi.mocked(api.reports.get)).toHaveBeenCalledWith(1);
    });
  });

  it("shows filter bar", async () => {
    render(<HistoryModule />);
    expect(screen.getByTestId("filter-bar")).toBeInTheDocument();
  });
});
