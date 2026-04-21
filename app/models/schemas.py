from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Urgency(str, Enum):
    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"
    emergency = "EMERGENCY"


class ChatMessageRequestType(str, Enum):
    text = "text"
    image = "image"
    report = "report"


class ChatRequestMetadata(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique ID for the conversation session")
    message: str = Field(..., min_length=1, max_length=4000)
    type: ChatMessageRequestType = Field(default=ChatMessageRequestType.text)
    metadata: Optional[ChatRequestMetadata] = None


class StructuredDiagnosis(BaseModel):
    summary: str
    possible_causes: List[str]
    advice: List[str]
    when_to_worry: List[str]
    recommended_doctors: List[str]
    risk: str


class ChatResponseData(BaseModel):
    message: str
    risk_level: Urgency
    follow_up_questions: List[str] = Field(default_factory=list)
    structured: Optional[StructuredDiagnosis] = None


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

class AnalyzeResponse(BaseModel):
    """Strict output schema used by all analyze endpoints."""
    summary: str = Field(..., min_length=1, max_length=4000)
    possible_causes: list[str] = Field(default_factory=list, max_length=12)
    advice: str = Field(..., min_length=1, max_length=4000)
    urgency: Urgency
