import type { ReportData } from "@/types";
import { ReportSection } from "./ReportSection";

const typeLabels: Record<string, string> = {
  befundbericht: "Befundbericht",
  therapiebericht_kurz: "Therapiebericht (kurz) \u2013 Verordnungsbericht",
  therapiebericht_lang: "Therapiebericht (lang) \u2013 Bericht auf besondere Anforderung",
  abschlussbericht: "Abschlussbericht",
};

interface ReportPreviewProps {
  report: ReportData;
}

export function ReportPreview({ report }: ReportPreviewProps) {
  return (
    <div className="rounded-lg border border-border overflow-hidden divide-y divide-border print:border-black print:divide-black print:text-black print:bg-white">
      {/* Header */}
      <div className="px-6 py-4 bg-surface print:bg-white">
        <h2 className="text-lg font-semibold print:text-black">
          {typeLabels[report.report_type] || report.report_type}
        </h2>
      </div>

      {/* Patient & Diagnose */}
      <ReportSection title="Patientendaten">
        <p><strong>Pseudonym:</strong> {report.patient.pseudonym}</p>
        <p><strong>Altersgruppe:</strong> {report.patient.age_group}</p>
        {report.patient.gender && <p><strong>Geschlecht:</strong> {report.patient.gender}</p>}
      </ReportSection>

      <ReportSection title="Diagnose">
        {report.diagnose.indikationsschluessel && (
          <p><strong>Indikationsschl&uuml;ssel:</strong> {report.diagnose.indikationsschluessel}</p>
        )}
        {report.diagnose.icd_10_codes.length > 0 && (
          <p><strong>ICD-10:</strong> {report.diagnose.icd_10_codes.join(", ")}</p>
        )}
        {report.diagnose.diagnose_text && <p>{report.diagnose.diagnose_text}</p>}
      </ReportSection>

      {/* Type-specific sections */}
      {report.report_type === "befundbericht" && (
        <>
          <ReportSection title="Anamnese">{report.anamnese}</ReportSection>
          <ReportSection title="Befund">{report.befund}</ReportSection>
          <ReportSection title="Therapieindikation">{report.therapieindikation}</ReportSection>
          {report.therapieziele && report.therapieziele.length > 0 && (
            <ReportSection title="Therapieziele">
              <ul className="list-disc list-inside space-y-1">
                {report.therapieziele.map((z, i) => <li key={i}>{z}</li>)}
              </ul>
            </ReportSection>
          )}
          <ReportSection title="Empfehlung">{report.empfehlung}</ReportSection>
        </>
      )}

      {report.report_type === "therapiebericht_kurz" && (
        <ReportSection title="Empfehlungen">{report.empfehlungen}</ReportSection>
      )}

      {report.report_type === "therapiebericht_lang" && (
        <>
          <ReportSection title="Therapeutische Diagnostik">{report.therapeutische_diagnostik}</ReportSection>
          <ReportSection title="Aktueller Krankheitsstatus">{report.aktueller_krankheitsstatus}</ReportSection>
          <ReportSection title="Aktueller Therapiestand">{report.aktueller_therapiestand}</ReportSection>
          <ReportSection title="Weiteres Vorgehen">{report.weiteres_vorgehen}</ReportSection>
        </>
      )}

      {report.report_type === "abschlussbericht" && (
        <>
          <ReportSection title="Therapieverlauf">{report.therapieverlauf_zusammenfassung}</ReportSection>
          <ReportSection title="Ergebnis">{report.ergebnis}</ReportSection>
          <ReportSection title="Empfehlung">{report.empfehlung}</ReportSection>
        </>
      )}
    </div>
  );
}
