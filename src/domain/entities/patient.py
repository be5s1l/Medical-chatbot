from dataclasses import dataclass


@dataclass
class PatientQuery:
    id: str
    text: str
    file_path: str | None = None
    vitals: dict | None = None

