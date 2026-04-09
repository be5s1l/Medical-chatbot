import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger

from src.controllers.file_ingestion import FileIngestionController, ImageIngestionController
from src.helpers.file_parser import detect_kind
from src.helpers.validators import DocumentUploadResponse, ImageUploadResponse

router = APIRouter(prefix="/upload", tags=["Upload"])

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_IMAGE_BYTES = 20 * 1024 * 1024

_file_controller: FileIngestionController | None = None
_image_controller: ImageIngestionController | None = None


def get_file_controller() -> FileIngestionController:
    global _file_controller
    if _file_controller is None:
        _file_controller = FileIngestionController()
    return _file_controller


def get_image_controller() -> ImageIngestionController:
    global _image_controller
    if _image_controller is None:
        _image_controller = ImageIngestionController()
    return _image_controller


@router.post("/document", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    try:
        data = await file.read()
        if len(data) > MAX_DOCUMENT_BYTES:
            raise HTTPException(status_code=413, detail="File too large (max 10MB)")
        suffix = Path(file.filename or "upload").suffix or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            path = tmp.name
        try:
            if detect_kind(path) != "document":
                raise HTTPException(status_code=400, detail="Expected a PDF document")
            out = get_file_controller().process_document(path)
            return DocumentUploadResponse(**out)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document upload error: {}", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/image", response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...)):
    try:
        data = await file.read()
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="File too large (max 20MB)")
        suffix = Path(file.filename or "upload").suffix or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            path = tmp.name
        try:
            if detect_kind(path) != "image":
                raise HTTPException(status_code=400, detail="Expected an image file")
            out = get_image_controller().process_image(path)
            return ImageUploadResponse(**out)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Image upload error: {}", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
