"""Lightweight keyword → ICD-10 chapter hints for demo (not a clinical coding system)."""

ICD10_HINTS: dict[str, str] = {
    "headache": "R51",
    "chest pain": "R07.9",
    "cough": "R05",
    "fever": "R50.9",
    "nausea": "R11.0",
    "diarrhea": "R19.7",
    "dizziness": "R42",
    "fatigue": "R53.83",
    "pain": "R52",
    "rash": "R21",
    "stroke": "I63.9",
    "bleeding": "R58",
}


def map_symptom_to_icd10(name: str) -> str | None:
    key = name.strip().lower()
    if key in ICD10_HINTS:
        return ICD10_HINTS[key]
    for phrase, code in ICD10_HINTS.items():
        if phrase in key:
            return code
    return None
