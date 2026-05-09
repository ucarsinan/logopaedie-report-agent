import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PatientForm } from "@/features/patients/PatientForm";

export default async function PatientBearbeitenPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <ErrorBoundary fallbackTitle="Patient bearbeiten nicht möglich">
      <PatientForm patientId={id} />
    </ErrorBoundary>
  );
}
