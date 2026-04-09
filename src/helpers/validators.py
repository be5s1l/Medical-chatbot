from pydantic import BaseModel, Field

from src.core.constants import DEFAULT_DISCLAIMER


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000, description="Patient symptom description")


class VitalsRequest(BaseModel):
    blood_pressure: str | None = Field(default=None)
    heart_rate: int | None = Field(None, ge=30, le=250)
    glucose_level: float | None = Field(None, ge=0, le=1000)
    temperature: float | None = Field(None, ge=30, le=45)


class ChatResponse(BaseModel):
    response: str
    triage_level: int
    conditions: list[str]
    source: str
    disclaimer: str


class DocumentUploadResponse(BaseModel):
    summary: str
    key_findings: list[str]
    response: str
    disclaimer: str = DEFAULT_DISCLAIMER
    phi_warning: str = (
        "Do not upload documents that contain personal identifiers unless you are authorized. "
        "Remove names, IDs, and addresses when possible."
    )


class ImageUploadResponse(BaseModel):
    classification: str
    confidence: float
    findings: list[str]
    disclaimer: str = DEFAULT_DISCLAIMER


class VitalsResponse(BaseModel):
    triage_level: int
    abnormal_readings: list[str]
    response: str
    disclaimer: str = DEFAULT_DISCLAIMER
