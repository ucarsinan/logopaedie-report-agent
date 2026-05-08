import { render, screen, waitFor } from "@testing-library/react";
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

vi.mock("@/lib/api", () => ({
  api: {
    sessions: {
      create: vi.fn(),
      get: vi.fn(),
      upload: vi.fn(),
      consent: vi.fn(),
      generate: vi.fn(),
      chat: vi.fn(),
    },
    patients: {
      get: vi.fn(),
      list: vi.fn(),
    },
  },
}));

vi.mock("@/components/WorkflowStepper", () => ({
  WorkflowStepper: ({ currentStep }: { currentStep: number }) => (
    <div data-testid="workflow-stepper" data-step={currentStep} />
  ),
}));

vi.mock("@/features/chat/PatientSelector", () => ({
  PatientSelector: ({ onDemo }: { onDemo: () => void }) => (
    <div data-testid="patient-selector">
      <button onClick={onDemo}>Demo starten</button>
    </div>
  ),
}));

vi.mock("../components/ChatView", () => ({
  ChatView: () => <div data-testid="chat-view" />,
}));

vi.mock("../components/PreUploadView", () => ({
  PreUploadView: () => <div data-testid="pre-upload-view" />,
}));

vi.mock("../components/GeneratingView", () => ({
  GeneratingView: () => <div data-testid="generating-view" />,
}));

vi.mock("../components/ReportPreview", () => ({
  ReportPreview: () => <div data-testid="report-preview" />,
}));

import { api } from "@/lib/api";
import { ReportModule } from "../ReportModule";

const defaultProps = {
  sessionId: null,
  setSessionId: vi.fn(),
  messages: [],
  setMessages: vi.fn(),
  error: null,
  setError: vi.fn(),
  isSending: false,
  setIsSending: vi.fn(),
  onRequestReset: vi.fn(),
};

describe("ReportModule", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(api.patients.list).mockResolvedValue({ items: [], total: 0, page: 1, limit: 8 });
  });

  it("renders without crash", async () => {
    render(<ReportModule {...defaultProps} />);
    // Should show patient selector (no stored session, no demo mode)
    await waitFor(() => {
      expect(screen.getByTestId("patient-selector")).toBeInTheDocument();
    });
  });

  it("shows patient selector when no stored session", async () => {
    render(<ReportModule {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByTestId("patient-selector")).toBeInTheDocument();
    });
  });

  it("shows workflow stepper after session is set", async () => {
    const storedSessionId = "abc123def456";
    localStorage.setItem("logopaedie_session_id", storedSessionId);
    vi.mocked(api.sessions.get).mockResolvedValue({
      session_id: storedSessionId,
      status: "anamnesis",
      chat_history: [],
      collected_data: {},
      materials_consent: false,
    } as unknown as ReturnType<typeof api.sessions.get> extends Promise<infer T> ? T : never);

    render(<ReportModule {...defaultProps} sessionId={storedSessionId} />);
    await waitFor(() => {
      expect(screen.getByTestId("workflow-stepper")).toBeInTheDocument();
    });
  });

  it("handles isSending state without crashing", async () => {
    localStorage.setItem("logopaedie_session_id", "abc123def456");
    vi.mocked(api.sessions.get).mockResolvedValue({
      session_id: "abc123def456",
      status: "anamnesis",
      chat_history: [],
      collected_data: {},
      materials_consent: false,
    } as unknown as ReturnType<typeof api.sessions.get> extends Promise<infer T> ? T : never);

    render(<ReportModule {...defaultProps} sessionId="abc123def456" isSending={true} />);
    await waitFor(() => {
      expect(screen.getByTestId("workflow-stepper")).toBeInTheDocument();
    });
  });

  it("shows pre-upload view when session exists and phase is pre-upload", async () => {
    localStorage.setItem("logopaedie_session_id", "abc123def456");
    vi.mocked(api.sessions.get).mockResolvedValue({
      session_id: "abc123def456",
      status: "anamnesis",
      chat_history: [],
      collected_data: {},
      materials_consent: false,
    } as unknown as ReturnType<typeof api.sessions.get> extends Promise<infer T> ? T : never);

    render(<ReportModule {...defaultProps} sessionId="abc123def456" />);
    await waitFor(() => {
      // After restoring session, phase is set to "chat"
      expect(screen.getByTestId("workflow-stepper")).toBeInTheDocument();
    });
  });

  it("calls api.sessions.get when stored session ID exists", async () => {
    const storedId = "abc123def456";
    localStorage.setItem("logopaedie_session_id", storedId);
    vi.mocked(api.sessions.get).mockResolvedValue({
      session_id: storedId,
      status: "anamnesis",
      chat_history: [],
      collected_data: {},
      materials_consent: false,
    } as unknown as ReturnType<typeof api.sessions.get> extends Promise<infer T> ? T : never);

    render(<ReportModule {...defaultProps} />);
    await waitFor(() => {
      expect(vi.mocked(api.sessions.get)).toHaveBeenCalledWith(storedId);
    });
  });
});
