from dataclasses import dataclass, field
from enum import IntEnum


class TriageLevel(IntEnum):
    EMERGENCY = 1  # Call emergency services immediately
    URGENT = 2  # Emergency department within ~1 hour
    SEMI_URGENT = 3  # See doctor today
    NON_URGENT = 4  # Appointment within days
    SELF_CARE = 5  # Home care may be appropriate


@dataclass
class TriageResult:
    level: TriageLevel
    conditions: list[str] = field(default_factory=list)
    response_text: str = ""
    source: str = "Medical Knowledge Base"
    disclaimer: str = (
        "This chatbot does not replace medical advice. "
        "Always consult a healthcare professional."
    )

