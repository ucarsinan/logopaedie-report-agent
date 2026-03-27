from pydantic import BaseModel


class MedicalReport(BaseModel):
    patient_pseudonym: str
    symptoms: list[str]
    therapy_progress: str
    prognosis: str
