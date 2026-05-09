import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PatientDetail } from "@/features/patients/PatientDetail";

export default async function PatientDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <ErrorBoundary fallbackTitle="Patientendetails nicht verfügbar">
      <PatientDetail patientId={id} />
    </ErrorBoundary>
  );
}
