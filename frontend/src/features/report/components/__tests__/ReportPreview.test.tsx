import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ReportPreview } from "../ReportPreview";
import type { ReportData } from "@/types";

const baseReport: ReportData = {
  report_type: "befundbericht",
  patient: { pseudonym: "P-001", age_group: "Erwachsen", gender: null },
  diagnose: {
    icd_10_codes: ["R47.1"],
    indikationsschluessel: "SP1",
    diagnose_text: "Aphasie",
  },
  anamnese: "Anamnese-Text",
  befund: "Befund-Text",
  therapieindikation: "Indikation-Text",
  therapieziele: ["Ziel A"],
  empfehlung: "Empfehlung-Text",
};

describe("ReportPreview", () => {
  it("announces the AI disclaimer via role=alert so screen readers hear it on render", () => {
    render(<ReportPreview report={baseReport} />);

    const disclaimer = screen.getByRole("alert");
    expect(disclaimer).toHaveTextContent(/KI-generierter Entwurf/);
    expect(disclaimer).toHaveTextContent(/fachlich prüfen/);
  });
});
