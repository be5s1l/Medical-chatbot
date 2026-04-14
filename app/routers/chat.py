from __future__ import annotations

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.models.schemas import AnalyzeResponse, ChatRequest
from app.services.groq_service import GroqService
from src.core.config import settings


router = APIRouter(tags=["Chat"])

_groq: GroqService | None = None


def _groq_service() -> GroqService:
    global _groq
    if _groq is None:
        _groq = GroqService()
    return _groq


@router.post("/chat", response_model=AnalyzeResponse)
async def chat(body: ChatRequest):
    try:
        try:
            out = await _groq_service().analyze(user_input=body.query)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return AnalyzeResponse(**out)
    except Exception as exc:
        logger.exception("Chat error")
        detail = str(exc) if settings.app_debug else "Internal server error"
        raise HTTPException(status_code=500, detail=detail) from exc

