import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    reports: {
      list: vi.fn(),
    },
    soap: {
      generate: vi.fn(),
      fromReport: vi.fn(),
      update: vi.fn(),
      getByReport: vi.fn(),
    },
  },
}));

const handleStaleSessionMock = vi.fn();
vi.mock("@/providers/SessionProvider", () => ({
  useSession: () => ({
    handleStaleSession: handleStaleSessionMock,
  }),
}));

import { api } from "@/lib/api";
import { SOAPModule } from "../SOAPModule";

/** Minimal ApiError stand-in: an Error with a numeric `status` field. */
class TestApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

const mockSOAPNote = {
  id: 1,
  subjective: "Patient berichtet von Schwierigkeiten beim Sprechen.",
  objective: "Dysarthrie Grad 2 festgestellt.",
  assessment: "Verbesserungspotenzial vorhanden.",
  plan: "2x wöchentlich Therapie.",
};

describe("SOAPModule", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.reports.list).mockResolvedValue({ items: [], total: 0, page: 1, limit: 20 });
    vi.mocked(api.soap.generate).mockResolvedValue(mockSOAPNote as unknown as ReturnType<typeof api.soap.generate> extends Promise<infer T> ? T : never);
  });

  it("renders without crash with no session", () => {
    render(<SOAPModule sessionId={null} />);
    expect(screen.getByText(/SOAP-Notizen/i)).toBeInTheDocument();
  });

  it("shows mode toggle buttons", async () => {
    render(<SOAPModule sessionId={null} />);
    expect(screen.getByText(/Aus aktueller Session/i)).toBeInTheDocument();
    expect(screen.getByText(/Aus gespeichertem Bericht/i)).toBeInTheDocument();
  });

  it("shows no session message when sessionId is null and session mode selected", async () => {
    render(<SOAPModule sessionId={null} />);
    // Session mode is default when sessionId is null? No - default is "report" when sessionId is null
    // Click session mode
    fireEvent.click(screen.getByText(/Aus aktueller Session/i));
    expect(screen.getByText(/Keine aktive Session/i)).toBeInTheDocument();
  });

  it("has a generate button when sessionId is provided", () => {
    render(<SOAPModule sessionId="abc123def456" />);
    expect(screen.getByText(/SOAP-Notiz generieren/i)).toBeInTheDocument();
  });

  it("fetches reports list when in report mode", async () => {
    render(<SOAPModule sessionId={null} />);
    // Default mode is "report" when sessionId is null
    await waitFor(() => {
      expect(vi.mocked(api.reports.list)).toHaveBeenCalledTimes(1);
    });
  });

  it("displays SOAP sections after generation", async () => {
    render(<SOAPModule sessionId="abc123def456" />);

    fireEvent.click(screen.getByText(/SOAP-Notiz generieren/i));

    await waitFor(() => {
      // After generation, soapNote is shown. Labels use "S — Subjektiv" etc.
      // The component renders <h4> with those labels
      expect(screen.queryByText("SOAP-Notiz")).toBeInTheDocument();
      // Check SOAP note content appears (in textareas since editing=true)
      const textareas = screen.getAllByRole("textbox");
      expect(textareas.length).toBeGreaterThan(0);
    });
  });

  it("shows error when generation fails", async () => {
    vi.mocked(api.soap.generate).mockRejectedValue(new Error("Verbindungsfehler"));
    render(<SOAPModule sessionId="abc123def456" />);

    fireEvent.click(screen.getByText(/SOAP-Notiz generieren/i));

    await waitFor(() => {
      expect(screen.getByText(/Verbindungsfehler/i)).toBeInTheDocument();
    });
  });

  it("recovers from a stale-session 404 on soap.generate by invoking the provider's handleStaleSession", async () => {
    // Backend signals the session no longer exists; component must NOT show a
    // plain error toast — it must delegate to the provider's recovery path.
    vi.mocked(api.soap.generate).mockRejectedValue(
      new TestApiError(404, "Session nicht gefunden oder abgelaufen."),
    );

    render(<SOAPModule sessionId="abc123def456" />);
    fireEvent.click(screen.getByText(/SOAP-Notiz generieren/i));

    await waitFor(() => {
      expect(handleStaleSessionMock).toHaveBeenCalledTimes(1);
    });

    // The component must not surface the raw backend message as a local error,
    // because handleStaleSession owns the user-facing toast + reset.
    expect(
      screen.queryByText(/Session nicht gefunden oder abgelaufen/i),
    ).not.toBeInTheDocument();
  });
});
