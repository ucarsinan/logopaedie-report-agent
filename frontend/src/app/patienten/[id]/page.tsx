import { PatientDetail } from "@/features/patients/PatientDetail";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PatientDetailPage({ params }: Props) {
  const { id } = await params;
  return <PatientDetail patientId={id} />;
}
