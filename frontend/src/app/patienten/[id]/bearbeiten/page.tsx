import { PatientForm } from "@/features/patients/PatientForm";

export default async function PatientBearbeitenPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <PatientForm patientId={id} />;
}
