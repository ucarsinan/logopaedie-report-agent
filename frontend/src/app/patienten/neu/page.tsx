import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PatientForm } from "@/features/patients/PatientForm";

export default function NeuerPatientPage() {
  return (
    <ErrorBoundary fallbackTitle="Patientenformular nicht verfügbar">
      <PatientForm />
    </ErrorBoundary>
  );
}
