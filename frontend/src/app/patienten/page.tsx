import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PatientList } from "@/features/patients/PatientList";

export default function PatientenPage() {
  return (
    <ErrorBoundary fallbackTitle="Patientenliste nicht verfügbar">
      <PatientList />
    </ErrorBoundary>
  );
}
