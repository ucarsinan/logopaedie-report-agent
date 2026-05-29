import { render, screen, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

const recordingState: { isRecording: boolean } = { isRecording: false };
const startRecording = vi.fn();
const stopRecording = vi.fn();
let capturedOnResult: ((blob: Blob) => void | Promise<void>) | null = null;

vi.mock("@/hooks/useAudioRecording", () => ({
  useAudioRecording: ({
    onResult,
  }: {
    onResult: (blob: Blob) => void | Promise<void>;
  }) => {
    capturedOnResult = onResult;
    return {
      isRecording: recordingState.isRecording,
      startRecording,
      stopRecording,
    };
  },
}));

vi.mock("@/lib/api", () => ({
  api: { transcribe: vi.fn() },
}));

vi.mock("@/components/icons", () => ({
  MicIcon: () => <svg data-testid="mic-icon" />,
  StopIcon: () => <svg data-testid="stop-icon" />,
}));

import { DictationButton } from "../DictationButton";
import { api } from "@/lib/api";

describe("DictationButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    recordingState.isRecording = false;
    capturedOnResult = null;
  });

  it("renders the idle mic button with an accessible label", () => {
    render(<DictationButton onTranscript={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: /Diktieren/i }),
    ).toBeInTheDocument();
  });

  it("labels the recording-state button as 'Aufnahme stoppen'", () => {
    recordingState.isRecording = true;
    render(<DictationButton onTranscript={vi.fn()} />);

    const stopButton = screen.getByRole("button", { name: /Aufnahme stoppen/i });
    expect(stopButton).toHaveAttribute("aria-label", "Aufnahme stoppen");
  });

  it("labels the pending-state button as 'Transkription läuft'", async () => {
    vi.mocked(api.transcribe).mockImplementation(
      () => new Promise(() => {}),
    );

    render(<DictationButton onTranscript={vi.fn()} />);

    expect(capturedOnResult).not.toBeNull();

    await act(async () => {
      // Fire onResult to flip the component into pending mode.
      // We never resolve api.transcribe → component stays in pending.
      void capturedOnResult!(new Blob());
    });

    const pendingButton = screen.getByRole("button", {
      name: /Transkription läuft/i,
    });
    expect(pendingButton).toBeDisabled();
  });
});
