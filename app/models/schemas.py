from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Urgency(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    emergency = "emergency"


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique ID for the conversation session")
    query: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    message: str
    is_final: bool = False
    empathy: Optional[str] = None
    summary: Optional[str] = None
    possible_causes: Optional[List[str]] = None
    what_you_can_do: Optional[str] = None
    when_to_be_concerned: Optional[str] = None
    recommended_specialist: Optional[str] = None
    disclaimer: Optional[str] = None
    risk_level: Optional[Urgency] = None


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
