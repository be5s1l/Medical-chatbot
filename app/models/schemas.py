from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Urgency(str, Enum):
    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"
    emergency = "EMERGENCY"


class ResponseType(str, Enum):
    """Discriminator that tells the client what action to take with this response."""
    chat = "chat"                # Normal conversational reply — display message to user
    get_doctors = "get_doctors"  # Tool call — client must fetch doctors and send results back


class UIComponentType(str, Enum):
    """
    Tells Flutter which input widget to render below the AI message.

    text     → plain message, no interactive input (just a chat bubble + free-text field)
    radio    → single-choice: mutually exclusive options (severity, yes/no, duration)
    checkbox → multi-choice: patient can pick several options (symptoms list, body areas)
    """
    text = "text"
    radio = "radio"
    checkbox = "checkbox"


class UIComponent(BaseModel):
    """
    Describes the Flutter widget the client should render for this turn.

    - `type`        : which widget to use
    - `options`     : the selectable choices (empty list for type=text)
    - `allow_other` : if True, Flutter must show an "Other..." option
                      that opens a free-text input so the patient can
                      type something not on the list
    """
    type: UIComponentType = UIComponentType.text
    options: List[str] = Field(
        default_factory=list,
        description="Selectable choices for radio / checkbox. Empty for text.",
    )
    allow_other: bool = Field(
        default=True,
        description="Show an 'Other...' free-text fallback option.",
    )


class ChatMessageRequestType(str, Enum):
    text = "text"


class ChatRequestMetadata(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None



class MedicalContext(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    conditions: List[str] = Field(default_factory=list)
    surgeries: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    lab_results: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Doctor search — tool-use models
# ---------------------------------------------------------------------------

class DoctorSearchParams(BaseModel):
    """Filter parameters extracted by the AI when the patient wants to find a doctor."""
    specialization: Optional[str] = Field(None, description="e.g. 'cardiologist', 'dermatologist'")
    location: Optional[str] = Field(None, description="City or area, e.g. 'Cairo'")
    min_rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Minimum star rating 0-5")


class DoctorResult(BaseModel):
    """A single doctor record returned by the client's doctor API."""
    id: str
    name: str
    specialization: str
    location: Optional[str] = None
    rating: Optional[float] = None
    clinic: Optional[str] = None
    available: Optional[bool] = None


class ToolResult(BaseModel):
    """Payload the client sends back after executing a tool call (e.g. get_doctors)."""
    tool: str = Field(..., description="Must match the tool name from the previous response, e.g. 'get_doctors'")
    doctors: List[DoctorResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Request / Response
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique ID for the conversation session")
    message: str = Field(default="", max_length=4000)
    type: ChatMessageRequestType = Field(default=ChatMessageRequestType.text)
    metadata: Optional[ChatRequestMetadata] = None
    medical_context: Optional[MedicalContext] = None
    tool_result: Optional[ToolResult] = Field(
        None,
        description="Set this when replying to a get_doctors tool call with the fetched doctor list.",
    )


class StructuredDiagnosis(BaseModel):
    summary: str
    possible_causes: List[str]
    advice: List[str]
    when_to_worry: List[str]
    recommended_doctors: List[str]
    risk: str


class ChatResponseData(BaseModel):
    type: ResponseType = Field(
        default=ResponseType.chat,
        description="'chat' = display message; 'get_doctors' = call your doctors API with search_params.",
    )
    message: str = Field(
        ...,
        description="Always a plain string. Never a list. The conversational text from the AI.",
    )
    risk_level: Urgency
    follow_up_questions: List[str] = Field(default_factory=list)
    structured: Optional[StructuredDiagnosis] = None
    search_params: Optional[DoctorSearchParams] = Field(
        None,
        description="Populated only when type='get_doctors'. Use these filters to query your doctors API.",
    )
    ui: UIComponent = Field(
        default_factory=UIComponent,
        description=(
            "Flutter widget hint for this turn. "
            "type=text → free chat; type=radio → single-choice buttons; "
            "type=checkbox → multi-select checkboxes. "
            "options contains the choices. allow_other adds an 'Other...' free-text fallback."
        ),
    )


class ErrorDetail(BaseModel):
    code: str
    message: str


class APIResponse(BaseModel):
    success: bool
    data: Optional[ChatResponseData] = None
    error: Optional[ErrorDetail] = None


class SessionState(BaseModel):
    session_id: str
    messages: List[Dict[str, str]] = Field(default_factory=list)
    symptoms: List[str] = Field(default_factory=list)
    duration: str = ""
    risk_level: str = ""
    flags: Dict[str, bool] = Field(default_factory=lambda: {"emergency": False})
    medical_context: Optional[Dict[str, Any]] = None


class AnalyzeResponse(BaseModel):
    """Strict output schema used by all analyze endpoints."""
    summary: str = Field(..., min_length=1, max_length=4000)
    possible_causes: list[str] = Field(default_factory=list, max_length=12)
    advice: str = Field(..., min_length=1, max_length=4000)
    urgency: Urgency
