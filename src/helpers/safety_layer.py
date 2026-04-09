from src.core.config import settings
from src.core.constants import DEFAULT_DISCLAIMER
from src.domain.entities.triage import TriageLevel, TriageResult


EMERGENCY_RESPONSE = (
    "EMERGENCY: Your described symptoms may be life-threatening. "
    "Call your local emergency number immediately or go to the nearest emergency department. "
    "Do not wait."
)


def check_emergency(text: str) -> bool:
    text_lower = (text or "").lower()
    return any(keyword in text_lower for keyword in settings.emergency_keywords_list)


def inject_disclaimer(response_text: str) -> str:
    return f"{response_text}\n\n---\n{DEFAULT_DISCLAIMER}"


def handle_emergency(query: str) -> TriageResult:
    _ = query  # reserved for future structured logging
    return TriageResult(
        level=TriageLevel.EMERGENCY,
        conditions=[],
        response_text=inject_disclaimer(EMERGENCY_RESPONSE),
        source="Safety Protocol",
        disclaimer=DEFAULT_DISCLAIMER,
    )

