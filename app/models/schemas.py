from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Urgency(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class AnalyzeResponse(BaseModel):
    """Strict output schema used by all analyze endpoints."""

    summary: str = Field(..., min_length=1, max_length=4000)
    possible_causes: list[str] = Field(default_factory=list, max_length=12)
    advice: str = Field(..., min_length=1, max_length=4000)
    urgency: Urgency


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=4000)

