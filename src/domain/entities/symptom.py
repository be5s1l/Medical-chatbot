from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


@dataclass
class SymptomEntity:
    name: str
    severity: Severity = Severity.MILD
    duration: str | None = None
    body_part: str | None = None
    icd10_code: str | None = None

