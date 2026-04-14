from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger

from app.models.schemas import AnalyzeResponse
from app.services.groq_service import GroqService
from app.services.pdf_service import PDFService, is_pdf
from src.core.config import settings
from src.core.constants import DEFAULT_DISCLAIMER


router = APIRouter(tags=["Lab"])

MAX_PDF_BYTES = 15 * 1024 * 1024

_groq: GroqService | None = None
_pdf: PDFService | None = None


def _groq_service() -> GroqService:
    global _groq
    if _groq is None:
        _groq = GroqService()
    return _groq


def _pdf_service() -> PDFService:
    global _pdf
    if _pdf is None:
        _pdf = PDFService()
    return _pdf


@router.post("/analyze-lab-pdf", response_model=AnalyzeResponse)
async def analyze_lab_pdf(file: UploadFile = File(...)):
    try:
        data = await file.read()
        if len(data) > MAX_PDF_BYTES:
            raise HTTPException(status_code=413, detail="File too large (max 15MB)")
        if not is_pdf(file.filename or "", file.content_type or ""):
            raise HTTPException(status_code=400, detail="Expected a PDF file")

        text = _pdf_service().extract_text(pdf_bytes=data, filename=file.filename or "upload.pdf")
        if not text.strip():
            raise HTTPException(status_code=422, detail="Could not extract text from PDF")

        user_input = (
            "This is text extracted from a lab report PDF.\n\n"
            f"{text}\n\n"
            "Simplify it for a patient. Highlight abnormal-looking values if present. "
            "Do not diagnose. Use possible causes. "
            f"Always include this disclaimer exactly: {DEFAULT_DISCLAIMER}"
        )
        try:
            out = await _groq_service().analyze(user_input=user_input)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return AnalyzeResponse(**out)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Analyze lab pdf error")
        detail = str(exc) if settings.app_debug else "Internal server error"
        raise HTTPException(status_code=500, detail=detail) from exc

