from fastapi import APIRouter, HTTPException
from loguru import logger

from src.core.config import settings
from src.controllers.symptom_triage import SymptomTriageController
from src.helpers.validators import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chat"])

symptom_controller: SymptomTriageController | None = None


def get_symptom_controller() -> SymptomTriageController:
    global symptom_controller
    if symptom_controller is None:
        symptom_controller = SymptomTriageController()
    return symptom_controller


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = get_symptom_controller().process(request.query)
        return ChatResponse(
            response=result.response_text,
            triage_level=result.level.value,
            conditions=result.conditions,
            source=result.source,
            disclaimer=result.disclaimer,
        )
    except Exception as e:
        logger.exception("Chat error")
        detail = str(e) if settings.app_debug else "Internal server error"
        raise HTTPException(status_code=500, detail=detail) from e
