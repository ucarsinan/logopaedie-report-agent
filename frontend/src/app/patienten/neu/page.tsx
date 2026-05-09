import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PatientForm } from "@/features/patients/PatientForm";

export default function NeuerPatientPage() {
  return (
    <ErrorBoundary fallbackTitle="Patientenliste nicht verfügbar">
      <PatientForm />
    </ErrorBoundary>
  );
}
