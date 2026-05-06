import { PatientForm } from "@/features/patients/PatientForm";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function PatientBearbeitenPage({ params }: Props) {
  const { id } = await params;
  return <PatientForm patientId={id} />;
}
