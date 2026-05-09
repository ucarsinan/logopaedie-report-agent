import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { PatientPickerModal } from "../PatientPickerModal";
import type { PatientSummary } from "@/types";

// Mock PatientSelector to avoid API calls in tests
vi.mock("@/features/chat/PatientSelector", () => ({
  PatientSelector: ({
    onSelect,
    onDemo,
  }: {
    onSelect: (patient: PatientSummary) => void;
    onDemo: () => void;
  }) => (
    <div>
      <p>Patient auswählen</p>
      <button
        type="button"
        onClick={() =>
          onSelect({
            id: "p1",
            pseudonym: "Test",
            system_id: "P-001",
            age_group: "adult",
            disorder_text: "Artikulationsstörung",
            created_at: "2026-01-01T00:00:00Z",
          })
        }
      >
        Patient wählen
      </button>
      <button type="button" onClick={onDemo}>
        Demo-Modus
      </button>
    </div>
  ),
}));

describe("PatientPickerModal", () => {
  const onSelect = vi.fn();
  const onDismiss = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders when open is true", () => {
    render(
      <PatientPickerModal open={true} onSelect={onSelect} onDismiss={onDismiss} />,
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Patient auswählen" })).toBeInTheDocument();
  });

  it("does not render when open is false", () => {
    render(
      <PatientPickerModal
        open={false}
        onSelect={onSelect}
        onDismiss={onDismiss}
      />,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("calls onDismiss when Demo button is clicked", () => {
    render(
      <PatientPickerModal open={true} onSelect={onSelect} onDismiss={onDismiss} />,
    );
    fireEvent.click(screen.getByText("Demo-Modus"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("calls onDismiss when Escape key is pressed", () => {
    render(
      <PatientPickerModal open={true} onSelect={onSelect} onDismiss={onDismiss} />,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("calls onSelect with the patient when a patient is chosen", () => {
    render(
      <PatientPickerModal open={true} onSelect={onSelect} onDismiss={onDismiss} />,
    );
    fireEvent.click(screen.getByText("Patient wählen"));
    expect(onSelect).toHaveBeenCalledWith({
      id: "p1",
      pseudonym: "Test",
      system_id: "P-001",
      age_group: "adult",
      disorder_text: "Artikulationsstörung",
      created_at: "2026-01-01T00:00:00Z",
    });
    expect(onDismiss).not.toHaveBeenCalled();
  });
});
