from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger

from app.models.schemas import AnalyzeResponse
from app.services.groq_service import GroqService
from app.services.ocr_service import OCRService
from app.services.vision_service import VisionService
from src.core.config import settings
from src.core.constants import DEFAULT_DISCLAIMER


router = APIRouter(tags=["Image"])

MAX_IMAGE_BYTES = 20 * 1024 * 1024
ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}

_groq: GroqService | None = None
_vision: VisionService | None = None
_ocr: OCRService | None = None


def _groq_service() -> GroqService:
    global _groq
    if _groq is None:
        _groq = GroqService()
    return _groq


def _vision_service() -> VisionService:
    global _vision
    if _vision is None:
        _vision = VisionService()
    return _vision


def _ocr_service() -> OCRService:
    global _ocr
    if _ocr is None:
        _ocr = OCRService()
    return _ocr


def _validate_image(file: UploadFile, data: bytes) -> None:
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix and suffix not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    if (file.content_type or "").lower() and not (file.content_type or "").lower().startswith("image/"):
        raise HTTPException(status_code=400, detail="Expected an image file")


@router.post("/analyze-image", response_model=AnalyzeResponse)
async def analyze_image(file: UploadFile = File(...)):
    """
    Flow:
    1) Vision model describes the image (non-diagnostic)
    2) Groq explains using strict JSON format + medical safety constraints
    """
    try:
        data = await file.read()
        _validate_image(file, data)

        try:
            vision_desc = await _vision_service().describe_image(
            image_bytes=data,
            mime_type=file.content_type or "image/png",
            )
        except RuntimeError as exc:
            # Misconfiguration (missing API key/model).
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        user_input = (
            "Image description (from vision model):\n"
            f"{vision_desc.description}\n\n"
            "Now provide a medical-safe explanation. "
            "Never diagnose. Use may/could/possible. "
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
        logger.exception("Analyze image error")
        detail = str(exc) if settings.app_debug else "Internal server error"
        raise HTTPException(status_code=500, detail=detail) from exc


@router.post("/analyze-lab-image", response_model=AnalyzeResponse)
async def analyze_lab_image(file: UploadFile = File(...)):
    """
    Flow:
    1) OCR (Tesseract / pytesseract if available)
    2) Clean text
    3) Groq simplifies into strict JSON output
    """
    try:
        data = await file.read()
        _validate_image(file, data)

        try:
            text = await _ocr_service().extract_text(
                image_bytes=data,
                filename=file.filename or "upload",
                mime_type=file.content_type or "",
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if not text.strip():
            raise HTTPException(status_code=422, detail="OCR produced empty text")

        user_input = (
            "This is OCR text extracted from a lab report image.\n\n"
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
        logger.exception("Analyze lab image error")
        detail = str(exc) if settings.app_debug else "Internal server error"
        raise HTTPException(status_code=500, detail=detail) from exc

