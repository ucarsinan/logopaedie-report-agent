import { PatientDetail } from "@/features/patients/PatientDetail";

export default async function PatientDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <PatientDetail patientId={id} />;
}
